import os
import datetime
import time
import sqlite3
from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from get_vector_db import get_vector_db
from langchain_core.messages import BaseMessage, AIMessage
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from flask import session
from tool_models import Subject, Class
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
import sys

# Redirect stdout to stderr
sys.stdout = sys.stderr

LLM_MODEL = os.getenv('LLM_MODEL', 'llama3.1:8b')
OLLAMA_SERVER_URL = os.getenv('OLLAMA_SERVER_URL', "http://localhost:11434")

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

#memory = MemorySaver()

weekDaysMapping = ("Monday", "Tuesday", 
                   "Wednesday", "Thursday",
                   "Friday", "Saturday",
                   "Sunday")
prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful virtual assistant named FIBerBot, developed by students at UPC(Universitat Politecnica de Barcelona), FIB (Facultat de informatica de barcelona).
                        Your goal is provide students at UPC the information they need.
                        You don't mention that you used tools, just summerize the tool call response.
                        Respode with the same language as the user's question.
                        Today is: {today}.
                        The day of the week is: {week}"""),
        ("placeholder", "{messages}"),])

class CustomState(TypedDict):
    today: str
    week: str
    messages: Annotated[list[BaseMessage], add_messages]
    is_last_step: str

def print_metrics(message : AIMessage):
    print("================================ Metrics ================================")
    print(f"\033[32mUsing model: {message.response_metadata['model']} \033[0m")
    print(f"\033[33mInput tokens: {message.usage_metadata['input_tokens']}")
    print(f"Output tokens: {message.usage_metadata['output_tokens']}\033[0m")
    print(f"\033[32mTotal tokens: {message.usage_metadata['total_tokens']}\033[0m")
    print(f"\033[34mLoad duration: {message.response_metadata['load_duration']/1e6} ms")
    print(f"Prompt evaluation duration: {message.response_metadata['prompt_eval_count']/1e6} ms")
    print(f"Evaluation duration: {message.response_metadata['eval_duration']/1e6} ms\033[0m")
    print(f"\033[32mTotal duration: {message.response_metadata['total_duration']/1e6} ms\033[0m")
    print(f"\033[32mTokens/s: {message.usage_metadata['output_tokens']/(message.response_metadata['total_duration']/1e9)} T/s\033[0m")

cost_per_million_tokens = {
    "llama3-70b-8192" : {
        "input" : 0.59,
        "output" : 0.79
    }
}

def print_cloud_compute_metrics(message: AIMessage):
    print("================================ Metrics ================================")
    model_name = message.response_metadata['model_name']
    print(f"\033[32mUsing model: {model_name} \033[0m")
    print(f"\033[33mInput tokens: {message.usage_metadata['input_tokens']}")
    print(f"Output tokens: {message.usage_metadata['output_tokens']}\033[0m")
    print(f"\033[32mTotal tokens: {message.usage_metadata['total_tokens']}\033[0m")
    print(f"\033[34mQueue time: {message.response_metadata['token_usage']['queue_time']*1000} ms")
    print(f"Prompt time: {message.response_metadata['token_usage']['prompt_time']*1000} ms")
    print(f"Completion time: {message.response_metadata['token_usage']['completion_time']*1000} ms\033[0m")
    print(f"\033[32mTotal time: {message.response_metadata['token_usage']['total_time']*1000} ms\033[0m")
    print(f"\033[32mTokens/s: {message.usage_metadata['output_tokens']/(message.response_metadata['token_usage']['total_time'])} T/s\033[0m")
    input_cost = (message.usage_metadata['input_tokens']/1e6)*cost_per_million_tokens[model_name]['input']
    output_cost = (message.usage_metadata['output_tokens']/1e6)*cost_per_million_tokens[model_name]['output']
    print("\033[33mInput Cost: " + '{0:.8f}'.format(input_cost) + "$")
    print("Output Cost: " + '{0:.8f}'.format(output_cost) + "$\033[0m")
    print("\033[32mTotal Cost: " + '{0:.8f}'.format(input_cost + output_cost) + "$\033[0m")
    return input_cost + output_cost



class Agent:
    def __init__(self, fib_api, token_key):
        # FIB API
        self.fib_api = fib_api
        self.token_key = token_key

        # Tools
        search = DuckDuckGoSearchRun()
        db = get_vector_db()
        retriever = db.as_retriever(search_kwargs={'k': 2})
        retrieval_tool = create_retriever_tool(
            retriever,
            "buscar_information_sobre_la_normativa_de_la_FIB",
            """
                Obtiene informacion sobre la normativa de la FIB (Facultat de Informatica de Barcelona),
                usalo cuando el usuari quera hacer una consulta sobre la normativa de la FIB, por ejemplo
                cuando el usuario pregunta 'Como funcion las practicas externas segun la normativa de la FIB'
            """,
        )
        self.tools=[retrieval_tool,
                    search,
                    self.natural_language_chat, 
                    self.get_subjects_list, 
                    self.get_subject_info, 
                    self.get_user_class_schedule]

    def get_urls(self):
        return self.fib_api.get('', headers={'Accept': 'application/json'}).data
    
    def natural_language_chat(self):
        """
        Conversa con el usuario. Usalo cuando ninguna de las otras funciones pueden resolver la pregunta del usuario,
        por ejemplo cuando el usuario saluda, da las gracias o se despide diciendo hola.
        """
        return "chat with the user"
    
    def get_subject_info(self, siglas):
        """
        Recupera informacion detallada sobre una asignatura de la lista de asignaturas que la universidad ofrece.
        Usalo cuando el usuario pregunta por la informacion de una asignatura, por ejemplo 'cuentame sobre la asignatura PTI'.

        Argumentos:
            siglas: las siglas de la asignatura.
            Por ejemplo en la pregunta 'cuentame sobre la asignatura PTI' las siglas serian PTI.
            Y si el usuario pregunta por una asignatura por su nombre, se tiene que traducir a sus siglas.
            Algunos ejemplos de nombres a siglas:
            Proyecto de Tecnologia de la Informacion, las siglas serian PTI.
        """
        session.get(self.token_key)
        urls = self.get_urls()
        subjects = self.fib_api.get(urls['public']['assignatures'], headers={'Accept' : 'application/json','Accept-Language': 'es'}).data
        for subject in subjects['results']:
            if subject['sigles'] == siglas:
                name = f"""name : {subject['nom']}"""
                detailed_info = self.fib_api.get(subject['guia'], headers={'Accept' : 'application/json', 'Accept-Language': 'es'}).data
                description = f"""description and metodologia_docent: {detailed_info['descripcio']} + {detailed_info['metodologia_docent']}"""
                teachers = f"""teachers : {detailed_info['professors']}"""
                department = f"""department: {detailed_info['departament']}"""
                evaluation = f"""evaluation methodology : {detailed_info['metodologia_avaluacio']}"""
                result = Subject(name, siglas, description, teachers, department, evaluation)
                return result
        return f"""No information about {siglas}"""
    
    def get_subjects_list(self):
        """
        Obtiene las asignaturas que el usuario esta matriculado.
        Usalo para saber que asignaturas el usuario esta actualmente matriculado,
        pro ejemplo cuando el usuario pregunta 'que asignaturas tengo este quadrimestre'
        """
        session.get(self.token_key)
        urls = self.get_urls()
        subjects = self.fib_api.get(urls['privat']['assignatures'], headers={'Accept' : 'application/json', 'Accept-Language': 'es'}).data
        names = []
        for subject in subjects['results']:
            names.append(subject['nom'])
        return names
    
    def get_user_class_schedule(self):
        """
        Obtiene el horario de clases del usuario.
        Usa esta funcion caundo el usuario pregunta por el horario de clases,
        por ejemplo cuando el usuario pregunta 'que clases tengo hoy'
        """
        session.get(self.token_key)
        urls = self.get_urls()
        schedule = self.fib_api.get(urls['privat']['horari'], headers={'Accept' : 'application/json', 'Accept-Language': 'es'}).data
        subjects = self.fib_api.get(urls['privat']['assignatures'], headers={'Accept' : 'application/json', 'Accept-Language': 'es'}).data
        clases = []
        for clase in schedule['results']:
            name = "name: " + clase['codi_assig']
            for subject in subjects['results']:
                if subject['id'] == clase['codi_assig']:
                    name = "name: " + subject['nom']
                    break
            grupo = "group: " + clase['grup']
            dia_semana = "day of the week: " + weekDaysMapping[clase['dia_setmana'] - 1]
            inicio = "start: " + clase['inici']
            durada = f"duration: {clase['durada']}"
            tipo = 'laboratory' if clase['tipus'] == "L" else 'teory'
            aula = "class rooms: " + clase['aules']
            clases.append(Class(name, grupo, dia_semana, inicio, durada, tipo, aula))
        return clases

    def query(self, input, thread_id, mode):
        if input:
            
            if mode == "local":
                start_time = time.monotonic()
                llm = ChatOllama(model=LLM_MODEL,base_url=OLLAMA_SERVER_URL)
                agent_executor = create_react_agent(llm, self.tools, checkpointer=memory, state_schema=CustomState, state_modifier=prompt, debug=False)
                config = {"configurable": {"thread_id": thread_id}}
                inputs = {"messages": [("user", f"{input}")], "today": f"{datetime.datetime.now()}", "week" : f"{weekDaysMapping[datetime.datetime.now().weekday()]}", "is_last_step" : ""}
                for chunk in agent_executor.stream(inputs, config, stream_mode="values"):
                    message = chunk["messages"][-1]
                    if isinstance(message, tuple):
                        print(message)
                    else:
                        message.pretty_print()
                    if isinstance(message, AIMessage):
                        print_metrics(message)
                end_time = time.monotonic()
                print(f"\033[31mTotal query execution time: {end_time - start_time} s\033[0m")
                return chunk['messages'][-1].content
            
            elif mode == "cloud":
                start_time = time.monotonic()
                llm = ChatGroq(model='llama3-70b-8192')
                agent_executor = create_react_agent(llm, self.tools, checkpointer=memory, state_schema=CustomState, state_modifier=prompt, debug=False)
                config = {"configurable": {"thread_id": thread_id}}
                inputs = {"messages": [("user", f"{input}")], "today": f"{datetime.datetime.now()}", "week" : f"{weekDaysMapping[datetime.datetime.now().weekday()]}", "is_last_step" : ""}
                query_cost = 0
                for chunk in agent_executor.stream(inputs, config, stream_mode="values"):
                    message = chunk["messages"][-1]
                    if isinstance(message, tuple):
                        print(message)
                    else:
                        message.pretty_print()
                    if isinstance(message, AIMessage):
                        query_cost += print_cloud_compute_metrics(message)
                end_time = time.monotonic()
                print(f"\033[31mTotal query execution time: {end_time - start_time} s")
                print("Total query cost: " + '{0:.8f}'.format(query_cost) +"$\033[0m")
                return chunk['messages'][-1].content
        return None