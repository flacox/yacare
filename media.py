#!/usr/bin/python3

import logging
import socket
import urllib.parse as up
import threading
import subprocess
import os, os.path, tempfile
import time
import json
import multiprocessing

logging.basicConfig(level=logging.DEBUG)

lock=threading.Lock()
bucle_activo=True
cancelar_reproduccion=False
reproducir_sgte=False
lista_rep=[]
lista_rep_nombre=''
lista_rep_idx=0
tipo_entrada_actual=''
token_entrada_actual='' # ruta|yt_id
proceso_player=None

def reproducir():
    global proceso_player
    global lista_rep_idx
    global cancelar_reproduccion, reproducir_sgte
    global tipo_entrada_actual, token_entrada_actual
    _cancelar=False
    _sgte=False
    _file_cookie=os.path.join(os.getcwd(), "yt_cookies")
    cmd_player=''
    logging.info("reproducir: iniciando reproducción...")
    while not _cancelar:
        time.sleep(0.3)
        lock.acquire()
        _cancelar=cancelar_reproduccion
        _sgte=reproducir_sgte
        if proceso_player==None and token_entrada_actual!='':
            if tipo_entrada_actual=='m' or tipo_entrada_actual=='v':
                cmd_player='/usr/bin/mplayer -input file=/tmp/fifo "%(ruta)s"'%{'ruta':token_entrada_actual}
            elif tipo_entrada_actual=='yt_video':
                cmd_player='/usr/bin/mplayer -input file=/tmp/fifo -cookies -cookies-file %(_file_cookie)s `/usr/bin/youtube-dl -f mp4 -g --cookies "%(_file_cookie)s" https://www.youtube.com/watch?v=%(yt_id)s`'%{'_file_cookie':_file_cookie, 'yt_id':token_entrada_actual}
            else:
                logging.info("reproducir: tipo de entrada no reconocida [%s]"%tipo_entrada_actual)
        if proceso_player==None and cmd_player!='':
            logging.info("reproducir: %s"%cmd_player)
            try:
                if os.path.exists('/tmp/fifo'): os.remove('/tmp/fifo')
                os.mkfifo('/tmp/fifo')
                proceso_player=subprocess.Popen(cmd_player, shell=True)
            except Exception as e:
                logging.error("reproducir: %s"%str(e))
        lock.release()
        if _cancelar:
            lock.acquire()
            if proceso_player!=None:
                logging.info("reproducir: deteniendo reproducción...")
                logging.info("reproducir: signal 9->%i"%proceso_player.pid)
                os.system('pkill -9 -P %i'%proceso_player.pid)
                proceso_player.terminate()
                proceso_player=None
            lock.release()
            if _sgte:
                lock.acquire()
                lista_rep_idx+=1
                if lista_rep_idx>=len(lista_rep):
                    logging.info("reproducir: no hay más elementos en la lista de reproducción")
                    lista_rep_idx=0
                    tipo_entrada_actual=''
                    token_entrada_actual=''
                    reproducir_sgte=False
                else:
                    tipo_entrada_actual=lista_rep[lista_rep_idx][0]
                    token_entrada_actual=lista_rep[lista_rep_idx][1]
                    cancelar_reproduccion=False
                    _cancelar=False
                lock.release()
    logging.info("reproducir: reproducción finalizada")
        
def procesar(data):
    global cancelar_reproduccion, reproducir_sgte
    global tipo_entrada_actual, token_entrada_actual
    global lista_rep
    global proceso_player
    respuesta='ok'
    try:
        parsed=up.urlparse(data[:-1])
        comando=parsed.path
        kwargs={} if parsed.query=='' else up.parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
        logging.info("procesar: [%s] %s"%(comando, str(kwargs)))
        #
        if comando=='/reproducir':
            #
            tipo_entrada=kwargs['tipo'][0]
            token_entrada=kwargs['ruta'][0]
            lock.acquire()
            cancelar_reproduccion=True
            tipo_entrada_actual=tipo_entrada
            token_entrada_actual=token_entrada
            lock.release()
            #
            lock.acquire()
            cancelar_reproduccion=False
            reproducir_sgte=True
            lock.release()
            #
            thrd=threading.Thread(target=reproducir)
            thrd.start()
        elif comando=='/detener':
            lock.acquire()
            cancelar_reproduccion=True
            reproducir_sgte=False
            tipo_entrada_actual=''
            token_entrada_actual=''
            lock.release()
        elif comando=='/pausar':
            lock.acquire()
            if proceso_player!=None:
                try:
                    with open('/tmp/fifo', 'wb') as arch:
                       arch.write('pause\n'.encode('utf-8'))
                except Exception as e:
                    logging.error("procesar: %s"%str(e))
            lock.release()
        elif comando=='/siguiente':
            lock.acquire()
            cancelar_reproduccion=True
            reproducir_sgte=True
            lock.release()
        elif comando=='/lista_agregar':
            tipo_entrada=kwargs['tipo'][0]
            token_entrada=kwargs['ruta'][0]
            lock.acquire()
            lista_rep.append((tipo_entrada, token_entrada))
            lock.release()
        elif comando=='/lista_obtener':
            _lista=[]
            lock.acquire()
            _lista=lista_rep
            lock.release()
            respuesta=json.dumps(_lista)
    except Exception as e:
        print(str(e))
    return respuesta

def principal():
    global bucle_activo, cancelar_reproduccion, reproducir_sgte
    logging.info("principal: iniciando...")
    sckt=socket.socket()
    sckt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    try:
        sckt.bind(('127.0.0.1', 8081))
        sckt.listen(10)
    except Exception as e:
        logging.error(str(e))
        return
    logging.info("principal: iniciando bucle principal...")
    while bucle_activo:
        conn=None
        try:
            logging.info("principal: esperando conexión...")
            conn, addr=sckt.accept()
            logging.info("principal: conexión establecida, recibiendo datos...")
            data=''
            while True:
                buffer=conn.recv(1024)
                if not buffer: break
                data+=buffer.decode('utf-8')
                if data.endswith('\n'): break
            logging.info("principal: datos recibidos (%i)"%len(data))
            logging.info("principal: procesando...")
            respuesta=procesar(data)
            respuesta+='\n'
            conn.sendall(respuesta.encode('utf-8'))
        except KeyboardInterrupt:
            logging.warning("principal: interrupción de teclado")
            bucle_activo=False
            lock.acquire()
            cancelar_reproduccion=True
            reproducir_sgte=False
            lock.release()
            time.sleep(2)
        except Exception as e:
            logging.error("principal: %s"%str(e))
            bucle_activo=False
            lock.acquire()
            cancelar_reproduccion=True
            reproducir_sgte=False
            lock.release()
            time.sleep(2)
        finally:
            logging.info("principal: cerrando conexión...")
            if conn!=None:
                conn.close()
                conn=None
    logging.info("principal: terminando...")
    sckt.shutdown(socket.SHUT_RDWR)
    sckt.close()
    logging.info("principal: terminado")

if __name__=='__main__':
    principal()
