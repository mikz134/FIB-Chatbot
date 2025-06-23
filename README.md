# FIB ChatBot
### Este es un proyecto para la assignatura PTI de la FIB del curso 2024-2025.
El proyecto tiene objetivo crear un ChatBot assistente para dar informacion de la FIB.
Utilizando NLP, LLMs, BBDD vectoriales y junto con una interfaz web utilizando Flask, logramos crear un Bot automatizado que busca sobre una base de datos informacion relevante y responde con lenguage natural a tus dudas sobre la FIB.

https://mwiki.fib.upc.edu/pti/index.php/Categor%C3%ADa:FIBerBot

# Configuración del sistema

## Fichero de configuración config.py
Este fichero debe contener el client id y client secret de un aplicación registrada en la API de la FIB. Para mas información hay un fichero de ejemplo en `config.py`

## variables de entorno
Ejemplo de `.env`
``` lua
SOURCE_FOLDER = './document_source'
CHROMA_PATH = 'chroma'
COLLECTION_NAME = 'fib-chatbot'
LLM_MODEL = 'llama3.1:8b'
TEXT_EMBEDDING_MODEL = 'nomic-embed-text'
```

# Instrucciones para iniciar el chatbot

## Instalar Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Iniciar Ollama
```bash
ollama serve &
```

## Descargar modelo
**Se puede descargar el modelo que se quiera, pero hay que configurarlo en .env para que funcione, se pueden consultar la lista de LLM disponibles para Ollama en https://ollama.com/**
```bash
ollama pull llama3.1:8b
```


## Descargar modelo de text embedding
```bash
ollama pull nomic-embed-text
```

## Docker
**En docker esta por defecto el modo solo CPU para el modo GPU investigat para habilitar vuestra GPU en docker**

## Despliegue
```bash
docker compose up
```

## Manual

## Iniciar el entorno virtual de python

```bash
python3 -m venv venv
source venv/bin/activate
```

## Instalar dependencias

```bash
pip install --no-cache-dir --no-deps -r requirements.txt
```

## Instalar Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Iniciar webapp
```bash
python3 app.py
```

Finalmente podras acceder a la aplicacion desde http://localhost:8080
