#!/bin/bash

CONTAINER_NAME="web-analyzer"
IMAGE_NAME="web-analyzer:latest"
PORT=8000

case "$1" in
    build)
        echo "Building Docker image..."
        docker build -t $IMAGE_NAME .
        
        # Save hash of requirements.txt for future comparison
        md5sum requirements.txt | cut -d' ' -f1 > .docker_build_hash
        echo "Build hash saved for requirements.txt"
        ;;
    start)
        echo "Starting web analyzer container..."
        docker run -d \
            --name $CONTAINER_NAME \
            -p $PORT:8000 \
            --env-file config.env \
            -v $(pwd)/logs:/app/logs \
            $IMAGE_NAME
        echo "Container started on port $PORT"
        ;;
    stop)
        echo "Stopping web analyzer container..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        echo "Container stopped and removed"
        ;;
    restart)
        echo "Restarting web analyzer container..."
        ./manage.sh stop
        sleep 2
        
        # Always rebuild to include latest code changes
        echo "Rebuilding image to include latest code changes..."
        ./manage.sh build
        
        ./manage.sh start
        ;;
    logs)
        echo "Showing container logs..."
        docker logs -f $CONTAINER_NAME
        ;;
    status)
        echo "Container status:"
        docker ps -a | grep $CONTAINER_NAME
        ;;
    shell)
        echo "Opening shell in container..."
        docker exec -it $CONTAINER_NAME /bin/bash
        ;;
    rebuild)
        echo "Force rebuilding Docker image..."
        docker build -t $IMAGE_NAME .
        md5sum requirements.txt | cut -d' ' -f1 > .docker_build_hash
        echo "Build hash saved for requirements.txt"
        ;;
    smart-restart)
        echo "Smart restart (only rebuilds if requirements.txt changed)..."
        ./manage.sh stop
        sleep 2
        
        # Check if requirements.txt has changed
        if [ -f ".docker_build_hash" ]; then
            current_hash=$(md5sum requirements.txt | cut -d' ' -f1)
            stored_hash=$(cat .docker_build_hash)
            
            if [ "$current_hash" != "$stored_hash" ]; then
                echo "Requirements.txt has changed, rebuilding image..."
                ./manage.sh build
            else
                echo "Requirements.txt unchanged, skipping rebuild..."
            fi
        else
            echo "No build hash found, rebuilding image..."
            ./manage.sh build
        fi
        
        ./manage.sh start
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|smart-restart|rebuild|logs|status|shell}"
        echo "  build        - Build Docker image"
        echo "  start        - Start container"
        echo "  stop         - Stop and remove container"
        echo "  restart      - Restart container (always rebuilds to include code changes)"
        echo "  smart-restart- Restart container (only rebuilds if requirements.txt changed)"
        echo "  rebuild      - Force rebuild Docker image"
        echo "  logs         - Show container logs"
        echo "  status       - Show container status"
        echo "  shell        - Open shell in container"
        exit 1
        ;;
esac
