import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask, redirect, request, jsonify, render_template, url_for, session, send_file
from flask_oauthlib.client import OAuth
from embed import embed, embed_url
from werkzeug import security
from agent import Agent
from agent import conn
from get_vector_db import get_vector_db
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

load_dotenv()
SOURCE_FOLDER = os.getenv('SOURCE_FOLDER', './document_source')
os.makedirs(SOURCE_FOLDER, exist_ok=True)

# Flask configuration
app = Flask(__name__)
app.config.from_object('config')
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_SECURE'] = True
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///'+os.path.join(basedir, 'db.sqlite')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)
app.app_context().push()
oauth = OAuth(app)
app_url = 'https://api.fib.upc.edu/v2/'
# OAuth UPC/FIB
def get_random_state():
    return security.gen_salt(16)

state = get_random_state()
fib = oauth.remote_app(
    'fib',
    request_token_params={'scope': 'read', 'state': state},
    base_url=app_url,
    request_token_url=None,
    access_token_method='POST',
    access_token_url=app_url + 'o/token/',
    authorize_url=app_url + 'o/authorize/',
    app_key='RACO'
)
token_key = 'api_token'

# Authentication check

@app.before_request
def enforce_authentication():
    if request.endpoint not in ['login', 'authorized', 'static', 'login_view'] and not request.cookies.get('authenticated'):
        session.clear()
        if request.endpoint == 'index':
            return redirect(url_for('login_view'))
        return jsonify({"message" : "No authenticated"}), 401

# login routes
@app.route('/login')
def login():
    return fib.authorize(callback=url_for('authorized', _external=True), approval_prompt='auto')

@app.route('/logout')
def logout():
    session.clear()
    response = redirect(url_for('login_view'))
    response.set_cookie('authenticated', '', expires=0)
    return response

@app.route('/login/authorized')
def authorized():
    resp = fib.authorized_response()
    received_state = request.args['state']
    if resp is None or resp.get('access_token') is None or received_state is None or received_state != state:
        return jsonify({"error": "access denied"}), 401
    else:
        session[token_key] = (resp['access_token'], '')
        response = redirect(url_for('index'))
        response.set_cookie(key="authenticated", value="True", max_age=3600)
        return response

#DB CHATS
class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    messages = db.relationship('Message', back_populates='chat', cascade='all, delete-orphan')

class ChatSchema(ma.Schema):
    class Meta:
        fields = ('id', 'title')

chatschema = ChatSchema()
chatschemas = ChatSchema(many = True)

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(50), db.ForeignKey('chats.id'),nullable=False)
    chat = db.relationship('Chat', back_populates='messages')
    role = db.Column(db.String(10), nullable=False)  # "human" o "ai"
    content = db.Column(db.Text, nullable=False)

class MessagesSchema(ma.Schema):
    class Meta:
        fields = ('id', 'chat_id', 'role', 'content')

messagechema = MessagesSchema()
messageschemas = MessagesSchema(many = True)

db.create_all()

#CREAR CHAT CON TITULO
#curl --request POST   --url http://localhost:8080/new_chat   --header 'Content-Type: application/json'   --data '{ "title": "TITLE" }'
@app.route('/new_chat', methods=['POST'])
def new_chat():
    data = request.get_json()

    title = data.get('title')
    
    if not title:
        return jsonify({"error": "El título es obligatorio"}), 400
    
    #existing_chat = Chat.query.filter_by(title=t).first()
    count = Chat.query.filter(Chat.title.like(f"{title}%")).count()

    if count:
        title = f"{title} ({count})"
    
    chat = Chat(title = title)
    db.session.add(chat)
    db.session.commit()
    result = chatschema.dump(chat)
    
    return jsonify({"chat": result}), 200

#BORRAR CHAT Y SUS MENSAJES DADO UN TITULO
#curl --request POST   --url http://localhost:8080/drop_chat/<chatid>'
@app.route('/drop_chat/<string:chatid>', methods=['DELETE'])
def drop_chat(chatid):
    chat = Chat.query.filter_by(id=chatid).first()

    #chat = Chat.query.get(chatid)

    if not chat:
        return jsonify({'error': 'Chat no encontrado'}), 404
    
    try:
        db.session.delete(chat)
        db.session.commit()
        sql1 = 'DELETE FROM checkpoints WHERE thread_id = ?'
        sql2 = 'DELETE FROM writes WHERE thread_id = ?'
        cur = conn.cursor()
        cur.execute(sql1, (chatid,))
        cur.execute(sql2, (chatid,))
        conn.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al eliminar el chat', 'details': str(e)}), 500

    return jsonify({'message': f'Chat con id {chatid} eliminado correctamente'}), 200

#BORRAR TODOS LOS CHATS Y SUS MENSAJES
#curl --request POST   --url http://localhost:8080/dropallchats
@app.route('/dropallchats', methods=['DELETE'])
def dropallchats():
    try:
        all_chats = Chat.query.all()

        for chat in all_chats:
            db.session.delete(chat)

        db.session.commit()

        db.session.delete(chat)
        db.session.commit()
        sql1 = 'DELETE FROM checkpoints'
        sql2 = 'DELETE FROM writes'
        cur = conn.cursor()
        cur.execute(sql1)
        cur.execute(sql2)
        conn.commit()
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al eliminar los chats', 'details': str(e)}), 500

    return jsonify({'message': 'Todos los chats y mensajes asociados fueron eliminados correctamente'}), 200

#DEVUELVE LISTADO DE LOS CHATS (SIN LOS MENSAJES)
#curl --request GET --url http://localhost:8080/chats
@app.route('/chats', methods=['GET'])
def get_chats():
    chats = Chat.query.all()
    result = chatschemas.dump(chats)

    return result, 200

#DEVUELVE MENSAJES ASOCIADOS AL CHAT CON TITLE
#curl --request GET --url http://localhost:8080/chats/<chatid>/messages
@app.route('/chats/<string:chatid>/messages', methods=['GET'])
def get_all_messages(chatid):
    chat = Chat.query.filter_by(id=chatid).first()
    
    if not chat:
        return jsonify({"error": f"No se encontró un chat con id '{chatid}'"}), 404

    messages = Message.query.filter_by(chat_id=chatid)
    result = messageschemas.dump(messages)

    return jsonify({'messages': result}), 200



# API routes

"""
curl --request POST \
  --url http://localhost:8080/query/<chatid> \
  --header 'Content-Type: application/json' \
  --data '{ "query": ""}'
"""
@app.route('/query/<string:chatid>', methods=['POST'])
def route_query(chatid):
    data = request.get_json()
    mode = data.get('mode')

    if mode == "cloud" and os.getenv("GROQ_API_KEY") == None:
        return jsonify({"error": "Missing groq cloud key"}), 400

    chat = Chat.query.filter_by(id=chatid).first()
    
    if not chat:
        return jsonify({"error": f"No se encontró un chat con id '{chatid}'"}), 404
    
    agent = Agent(fib, token_key)
    response = agent.query(input=data.get('query'), thread_id=chatid, mode=mode)
    
    message = Message(chat_id=chatid, role="human", content=data.get('query'))
    db.session.add(message)

    message = Message(chat_id=chatid, role="ai", content=response)
    db.session.add(message)
    db.session.commit()

    if response:
        return jsonify({"message": response, "chatId":chatid}), 200
    
    db.session.rollback()
    return jsonify({"error": "Something went wrong"}), 400


# vector database CRUD

@app.route('/embed_pdf', methods=['POST'])
def route_embed_pdf():
    if 'file' in request.files:
        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        embedded = embed(file)

        if embedded:
            return jsonify({"message": "File embedded successfully"}), 200

    return jsonify({"error": "File embedded unsuccessfully"}), 400

@app.route('/embed_url', methods=['POST'])
def route_embed_url():
    
    data = request.get_json()
    embedded = embed_url(data.get('url'))
   
    if embedded:
        return jsonify({"message": "URL embedded successfully"}), 200

    return jsonify({"error": "URL embedded unsuccessfully"}), 400

@app.route('/get_all_sources')
def get_all_sources():
    vector_store = get_vector_db()
    docs = vector_store.get(include=["metadatas"])
    metadata_list = docs['metadatas']

    # Extract unique sources from metadata
    unique_sources = set([metadata["source"] for metadata in metadata_list])
    source_list = [item.replace(SOURCE_FOLDER + "/", "") if item.startswith(SOURCE_FOLDER + "/") else item for item in list(unique_sources)]
    
    return jsonify({"sources" : source_list})

@app.route('/delete_source', methods=['DELETE'])
def delete_source():
    data = request.get_json()
    source = data.get('source')

    # check if source is pdf
    if '.' in source and source.rsplit('.', 1)[1].lower() in {'pdf'}:
        source = SOURCE_FOLDER + "/" + source
        os.remove(source)

    vector_store = get_vector_db()
    docs = vector_store.get(where={'source': source})
    doc_ids = docs['ids']
    vector_store.delete(doc_ids)
    return jsonify({"document_deleted" : doc_ids})


@fib.tokengetter
def get_raco_token():
    return session.get(token_key)

@app.route('/login_view')
def login_view():
    return render_template('login_view.html', title='FiberBot', message='Hello, Flask!')

@app.route('/')
def index():
    return render_template('index.html', title='FiberBot', message='Hello, Flask!')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
