import random
import socket
import os
import struct
import select
import time


# Вычисление контрольной суммы ICMP пакета
def checksum(source_string):
    sum = 0
    max_count = (len(source_string) / 2) * 2
    count = 0
    while count < max_count:
        val = source_string[count + 1] * 256 + source_string[count]
        sum = sum + val
        sum = sum & 0xffffffff
        count = count + 2

    if max_count < len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


# Создание ICMP Echo запроса
def create_echo_request(id, seq_number, payload):
    # заголовок состоит из типа (8), кода (8), контрольной суммы (16), идентификатора (16) и номера последовательности (16)
    header = struct.pack('bbHHh', 8, 0, 0, id, seq_number)
    data = header + payload
    my_checksum = checksum(data)

    header = struct.pack('bbHHh', 8, 0, socket.htons(my_checksum), id, seq_number)
    return header + payload


# Отправка ICMP Echo запроса и ожидание ответа
def ping(dest_addr, iface=None, timeout=1, payload=b''):
    try:
        # Создание сырого сокета ICMP
        icmp = socket.getprotobyname('icmp')
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)

        # Привязка к интерфейсу, если задан
        if iface:
            sock.setsockopt(socket.SOL_SOCKET, 25, str(iface + '0').encode('utf-8'))
        packet_id = int((id(timeout) * random.random()) % 65535)
        packet = create_echo_request(packet_id, 1, payload)
        sent = sock.sendto(packet, (dest_addr, 1))

        delay = receive_ping(sock, packet_id, time.time(), timeout)
        sock.close()
        return delay
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


# Получение ICMP Echo ответа
def receive_ping(sock, packet_id, time_sent, timeout):
    while True:
        ready = select.select([sock], [], [], timeout)
        time_received = time.time()
        if ready[0] == []:  # Timeout
            return None

        rec_packet, addr = sock.recvfrom(1024)
        icmp_header = rec_packet[20:28]
        type, code, checksum, p_id, sequence = struct.unpack('bbHHh', icmp_header)

        if p_id == packet_id:  # Проверка идентификатора пакета
            return time_received - time_sent

    return None


# Пример использования
if __name__ == "__main__":
    dest_ip = '10.8.0.1'  # Примерный IP адрес для теста PING
    iface = 'Nick-Laptop'  # Имя интерфейса WireGuard

    print(f"Pinging {dest_ip} on interface {iface}:")
    delay = ping(dest_ip)#, iface=iface)
    if delay:
        print(f"Ответ от {dest_ip} за {delay * 1000:.2f}ms")
    else:
        print("Таймаут ожидания ответа от хоста.")
