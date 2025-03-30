#!/bin/bash

# Параметры VM
FOLDER_ID="b1g1dqndjm3242cgelih"            # ID каталога
ZONE="ru-central1-a"                        # Зона доступности
VM_NAME="fastapi-hw3"                      # Имя VM
SUBNET_ID=e9b09b0ifep0t2so7iui              # ID подсети
SERVICE_ACCOUNT_ID="ajels7qcnortm84jq8b7"   # ID сервисного аккаунта (с правами на чтение образов из Container Registry)
PLATFORM_ID="standard-v3"                   # Платформа
CORES=4                                     # Количество ядер
MEMORY=8GB                                  # Объем памяти в ГБ
DISK_SIZE=30                                # Размер диска в ГБ
DOCKER_COMPOSE_PATH="./docker-compose.yml"
SSH_KEY_PATH=~/.ssh/id_ed25519.pub
# STATIC_IP="51.250.66.13"                    # статический IP для доступа к сервису

# Проверка наличия необходимых утилит
command -v yc >/dev/null 2>&1 || { echo "Error: yc utility is not installed"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "Error: jq utility is not installed"; exit 1; }

# Проверка наличия необходимых файлов
if [ ! -f "$DOCKER_COMPOSE_PATH" ]; then
    echo "Error: docker-compose file not found at path: $DOCKER_COMPOSE_PATH"
    exit 1
fi

if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "Error: SSH key not found at path: $SSH_KEY_PATH"
    exit 1
fi

# Парсинг аргументов
RESET=false
DELETE=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --reset) RESET=true ;;
        --delete) DELETE=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Если указан параметр --delete, удаляем ВМ и завершаем работу
if [ "$DELETE" = true ]; then
    if yc compute instance get ${VM_NAME} > /dev/null 2>&1; then
        echo "Deleting VM ${VM_NAME}..."
        yc compute instance delete ${VM_NAME}
        echo "VM ${VM_NAME} successfully deleted"
    else
        echo "VM ${VM_NAME} does not exist"
    fi
    exit 0
fi


# Проверка наличия VM с таким же именем
if yc compute instance get ${VM_NAME} > /dev/null 2>&1; then
    # Получение статуса VM
    STATUS=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.status')
    if [ "$STATUS" = "RUNNING" ] && [ "$RESET" = false ]; then
        echo "VM ${VM_NAME} is already running. No action needed."
        # Получение внешнего IP
        EXTERNAL_IP=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
        echo "VM external IP: ${EXTERNAL_IP}"
        exit 0
    else
        echo "VM ${VM_NAME} is in status: $STATUS. Deleting..."
        yc compute instance delete ${VM_NAME} --async
        # Ожидание удаления
        while true; do
            STATUS=$(yc compute instance get ${VM_NAME} --format=json 2>/dev/null | jq -r '.status')
            if [ -z "$STATUS" ]; then
                echo "VM ${VM_NAME} successfully deleted."
                break
            elif [ "$STATUS" = "DELETING" ]; then
                echo "Waiting for VM ${VM_NAME} to be deleted..."
                sleep 15
            else
                echo "Error deleting VM ${VM_NAME}. Status: $STATUS"
                exit 1
            fi
        done
    fi
fi

# Создание VM с Container Solution
yc compute instance create-with-container \
  --name ${VM_NAME} \
  --zone ${ZONE} \
  --cores ${CORES} \
  --memory ${MEMORY} \
  --ssh-key ${SSH_KEY_PATH} \
  --platform-id ${PLATFORM_ID} \
  --create-boot-disk size=${DISK_SIZE} \
  --network-interface subnet-id=${SUBNET_ID},nat-ip-version=ipv4 \
  --service-account-id ${SERVICE_ACCOUNT_ID} \
  --docker-compose-file ${DOCKER_COMPOSE_PATH} \
#   --preemptible


# Проверка статуса создания
echo "Waiting for VM creation..."
while true; do
    STATUS=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.status')
    if [ "$STATUS" = "RUNNING" ]; then
        echo "VM successfully created and running"
        break
    elif [ "$STATUS" = "ERROR" ]; then
        echo "Error creating VM"
        exit 1
    fi
    sleep 5
done

# Получение внешнего IP
EXTERNAL_IP=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
echo "VM external IP: ${EXTERNAL_IP}"