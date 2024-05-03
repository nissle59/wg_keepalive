import configparser
import json
import logging
import sys
import subprocess
import pathlib
from ping_pong import *

handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
s_handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.addHandler(s_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# Параметры конфигурации
wg_interface = 'wg0'
srv_cnf_file = pathlib.Path('server.conf')
server_config = configparser.ConfigParser()
server_config.read(srv_cnf_file)
srv_vpn_ip = server_config['Interface']['Address'].split('/')[0]


def up():
    with open('server.conf', 'r', encoding='utf-8') as fd:
        config_data = fd.read()
    config_path = f'/etc/wireguard/{wg_interface}.conf'

    # Пишем данные в конфигурационный файл
    if not pathlib.Path('/etc/wireguard').exists():
        pathlib.Path('/etc/wireguard').mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as fd:
        fd.write(config_data)

    # Поднимаем WireGuard интерфейс с помощью wg-quick
    try:
        subprocess.run(['wg-quick', 'up', wg_interface], check=True)
        logger.info(f"Туннель {wg_interface} успешно поднят.")
    except subprocess.CalledProcessError:
        logger.info(f"Ошибка при попытке поднять туннель {wg_interface}.")

if __name__ == '__main__':
    with open('srv.log', 'a', encoding='utf-8') as f_log:
        while True:
            delay = ping(srv_vpn_ip)
            if delay:
                logger.info('Сервер запущен и работает')
                time.sleep(1)
            else:
                up()