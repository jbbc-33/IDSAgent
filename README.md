INSTRUCCIONES para iniciar el entorno

0. Instalacion de dependencias

La version de python utilizada para el proyecto es la 3.11.9

En el directorio /Proyecto

Ejecutar en bash:
pip install -r requirements.txt

Esto instalara las librerias del entorno de python donde se ha probado el proyecto, es recomendable crear un entorno virtual para instalarlas

Instalar Ollama

El proyecto se ha probado con un LLM local de ollama, en concreto se ha usado el modelo qwen2.5:3b

Ejecutar en bash:
curl -fsSL https://ollama.com/install.sh | bash

Para instar Ollama

Ejecutar en bash:
ollama run qwen2.5:3b

Una vez que tenemos ollama instalado, instalamos y corremos el llm, esto lo hara automaticamente.

1. En el directorio /Proyecto/Docker

Ejecutar en bash:
sudo docker compose up -d

Para levantar los contenedores docker de opensearch y el dashboard

2. En el directorio /Proyecto/Configuracion

Ejecutar en bash:
python set_up_embedding_pipeline.py

Para crear el pipeline embedding de ingesta de opensearch

3. En el directorio /Proyecto/Configuracion

Ejecutar en bash:
python ingestion.py

Para crear el indice de opensearch y llenarlo con los logs de entrenamiento (en nuestro caso almacenados en Proyecto/data/train-logs-dataset.csv)

4. (OPCIONAL) (SOLUCION DE ERRORES)

Por problemas internos de opensearch normalmente cuando intentas llenar el indice creado en el paso 3, ocurre un error y el contenedor principal
de opensearch cae, cuando ocurra esto, hay que volver a ejecutar los pasos 1 2 y 3 en el orden establecido, y esta vez debe de funcionar correctamente
(se puede saber cuando los logs se terminan de ingerir correctamente sin lanzar excepciones)

5. (OPCIONAL) En el directorio /Proyecto/Agentes/MCP_Server

Ejecutar en bash:
python mcp_server.py

Para poner en funcionamiento el mcp server, este servidor permite a los agentes descubrir la tool de RAG, ayudandolos con su evaluacion, los agentes
pueden trabajar correctamente sin ninguna tool, por eso este paso es opcional

6. En el directorio /Proyecto/Agentes/Agente1

Ejecutar en bash:
python __main__.py

Esto levantara al primer agente (por defecto en el archivo ids_graph.py ya lleva la consulta a un log de ejemplo, en la funcion main2() )

7. (OPCIONAL) En el directorio /Proyecto/Agentes/Agente2

Ejecutar en bash:
python __main__.py

Esto levantara al segundo agente (por defecto en el archivo ids_graph.py ya lleva la consulta a un log de ejemplo, en la funcion main2() ).
Este segundo agente es igual al primero, este paso es opcional ya que un agente es capaz de evaluar logs por si mismo, pero
si hay mas agentes disponibles, en caso de que se vea precisado, puede consultarles para disponer de una segunda opinion.