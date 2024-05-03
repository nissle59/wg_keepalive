import configparser
import subprocess
import pathlib
import sys
import time
import logging

handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
s_handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.addHandler(s_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

from ping_pong import *

cnf_file = pathlib.Path('client.conf')
srv_cnf_file = pathlib.Path('server.conf')
wg_interface = 'wg0'

client_config = configparser.ConfigParser()
client_config.read(cnf_file)
server_config = configparser.ConfigParser()
server_config.read(srv_cnf_file)
srv_vpn_ip = server_config['Interface']['Address'].split('/')[0]
cli_vpn_ip = client_config['Interface']['Address'].split('/')[0]
srv_glob_addr = client_config['Peer']['Endpoint'].split(':')[0]


def up():
    try:
        subprocess.run(['wg-quick', 'down', wg_interface], check=True)
    except Exception as e:
        logger.info(e)
    with open(cnf_file, 'r', encoding='utf-8') as fd:
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
    fails = 0
    max_fails = 5
    try:
        up()
    except Exception as e:
        logger.error(e)
    while True:
        if fails >= max_fails:
            up()
            time.sleep(5)
        delay = ping(srv_glob_addr)
        if delay:
            delay = ping(srv_vpn_ip, timeout=5)
            if delay:
                logger.info(f"Ответ от {srv_vpn_ip} за {delay * 1000:.2f}ms")
                fails = 0
                time.sleep(1)
            else:
                logger.info(f"VPN туннель живой мертвец {cli_vpn_ip} <-> {srv_vpn_ip}")
                fails += 1
                time.sleep(5)
        else:
            logger.info("Сервер VPN недоступен")
