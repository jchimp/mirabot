## 1. Create project directory
    ```
    mkdir mirabot && cd mirabot
    ```

## 2. Download Piper voice model
Windows:
    ```
    mkdir -p piper-models
    cd piper-models
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -OutFile en_US-lessac-medium.onnx 
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -OutFile en_US-lessac-medium.onnx.json 
    cd ..
    ```

Linux:
    ```
    mkdir -p piper-models
    cd piper-models
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
    cd ..
    ```

## 3a. If running Ollama local:
    ```
    ollama pull llama3
    ```
    - If on Windows, also enable Network Access in Ollama setting
    - Open Windows Firewall for TCP/UDP 11434
    - Edit System ENV to set docker to run on all IPs, not just localhost (127.0.0.1) 
        - OLLAMA_HOST=0.0.0.0
        - Restart Ollama

## 3b. If running Ollama as Docker Container:
### Pull Ollama model (after compose is up)
    ```
    docker exec mirror-ollama ollama pull llama3
    ```

## 4. Create Flash Secret and set in config.yaml
==TODO: CODE==

## 5. Start my-mirra
    ```
    docker compose up -d --build
    ```