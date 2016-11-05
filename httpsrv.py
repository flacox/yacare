#!/usr/bin/python3

import cherrypy
import socket
import jinja2
import os
import urllib.parse as up
import apiclient.discovery as ytapi

class SistemaDeArchivos:
    
    def __init__(self):
        self.dirs_media=['/home/flaco/media']
        self.extensiones={
                                    'musica':['mp3', 'wav', 'flac', 'ogg'], 
                                    'video':['mkv', 'avi', 'mpg', 'mp4'], 
                                    'subtitulos':['srt', 'sub']
                                    }

    def _ruta_de_id_entrada(self, id_entrada):
        partes_id=id_entrada.split("_")
        for i in range(len(partes_id)):
            idx_entrada=int(partes_id[i])
            if i==0:
                ruta=self.dirs_media[idx_entrada]
                continue
            entradas=os.listdir(ruta)
            entrada=entradas[idx_entrada]
            ruta=os.path.join(ruta, entrada)
        return ruta

    def _id_entrada_padre(self, id_entrada):
        if id_entrada==None:
            return ''
        idp, sep, idx=id_entrada.rpartition("_")
        return idp

    def _datos_entrada(self, ruta, id_entrada): # -> {id, tipo, etiqueta, extension}
        if os.path.isdir(ruta):
            return {'id':id_entrada, 
                         'tipo':'d', 
                         'etiqueta':os.path.basename(ruta),
                         'extension':''
                        }
        nombre=os.path.basename(ruta)
        etiqueta=''
        extension=''
        try:
            etiqueta, separador, extension=nombre.rpartition('.')
        except ValueError:
            return {'id':id_entrada, 
                         'tipo':'n', 
                         'etiqueta':'', 
                         'extension':''
                        }
        tipo=''
        if extension in self.extensiones['musica']:
            tipo='m'
        elif extension in self.extensiones['video']:
            tipo='v'
        elif extension in self.extensiones['subtitulos']:
            tipo='s'
        else:
            return {'id':id_entrada,
                         'tipo':'n',
                         'etiqueta':'',
                         'extension':''
                        }
        return {'id':id_entrada, 
                     'tipo':tipo, 
                     'etiqueta':etiqueta,
                     'extension':extension
                    }

class Youtube:
    
    def __init__(self, jj):
        self.jj=jj
        #
        self.DEVELOPER_KEY = "AIzaSyCfflFDLE_k0rRxzEO44eDSgkodDfOwF6Y"
        self.YOUTUBE_API_SERVICE_NAME = "youtube"
        self.YOUTUBE_API_VERSION = "v3"
    
    @cherrypy.expose
    def index(self, c=None):
        _entradas=self._buscar(c)
        template=self.jj.get_template("yt.html")
        return template.render(entradas=_entradas)

    def _buscar(self, consulta):
        _entradas=[]
        if consulta==None:
            return _entradas
        yt=ytapi.build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION, developerKey=self.DEVELOPER_KEY)
        resultado=yt.search().list(q=consulta, part='id,snippet', maxResults=10).execute()
        for item in resultado.get("items", []):
            itKindId=None
            tipo=None
            if item['id']['kind']=='youtube#video':
                itKindId=item['id']['videoId']
                tipo='yt_video'
            elif item['id']['kind']=='youtube#channel':
                itKindId=item['id']['channelId']
                tipo='yt_channel'
            elif item['id']['kind']=='youtube#playlist':
                itKindId=item['id']['playlistId']
                tipo='yt_playlist'
            entrada={'id':itKindId, 
                            'tipo':tipo, 
                            'etiqueta':item['snippet']['title'], 
                            'extension':''
                            }
            _entradas.append(entrada)
        #
        return _entradas

class Yacare:
    
    def __init__(self):
        self.jj=jinja2.Environment(loader=jinja2.FileSystemLoader('./templates'))
        self.sa=SistemaDeArchivos()
        self.yt=Youtube(self.jj)
        self.id_entrada="0"
        
    @cherrypy.expose
    def index(self):
        tpl=self.jj.get_template('index.html')
        return tpl.render()
    
    @cherrypy.expose
    @cherrypy.popargs('comando')
    def cmd(self, comando):
        cherrypy.log("Yacare[cmd]: %s"%comando)
        respuesta=self._enviar_comando(comando, {})
        return respuesta

    @cherrypy.expose
    @cherrypy.popargs('id_entrada')
    def listar_dir(self, id_entrada=None):
        if id_entrada!=None:
            self.id_entrada=id_entrada
        id_padre=self.sa._id_entrada_padre(self.id_entrada)
        datos_entradas=[]
        ruta=self.sa._ruta_de_id_entrada(self.id_entrada)
        entradas=[os.path.join(ruta, entrada) for entrada in os.listdir(ruta)]
        for i in range(len(entradas)):
            entrada=entradas[i]
            #print(entrada)
            datos_entrada=self.sa._datos_entrada(entrada, "_".join([self.id_entrada, str(i)]))
            if not datos_entrada['tipo']=='n':
                datos_entradas.append(datos_entrada)
        datos_entradas.sort(key=lambda x:x['etiqueta'].lower())
        template=self.jj.get_template("listar_dir.html")
        return template.render(id_entrada_padre=id_padre, ruta_dir=ruta, lista=datos_entradas)

    @cherrypy.expose
    @cherrypy.popargs('tipo')
    @cherrypy.popargs('id_entrada')
    def reproducir(self, tipo, id_entrada):
        cherrypy.log("Yacare[reproducir]: %s"%id_entrada)
        respuesta=''
        datos=None
        ruta=''
        if tipo=='m' or tipo=='v':
            ruta=self.sa._ruta_de_id_entrada(id_entrada)
            datos=self.sa._datos_entrada(ruta, id_entrada)
            datos['ruta']=ruta
        elif tipo=='yt_video':
            datos={'id':id_entrada, 
                        'tipo':tipo, 
                        'etiqueta':'', 
                        'extension':'', 
                        'ruta':id_entrada
                        }
        url="/reproducir?%s\n"%up.urlencode(datos)
        sckt=socket.socket()
        try:
            sckt.connect(('127.0.0.1', 8081))
            sckt.sendall(url.encode('utf-8'))
            cherrypy.log("Yacare[reproducir]: esperando respuesta...")
            buffer=sckt.recv(1024)
            respuesta=buffer.decode('utf-8')
        except Exception as e:
            cherrypy.log("Yacare[reproducir]: %s"%str(e))
        finally:
            sckt.close()
        return respuesta
            
    def _enviar_comando(self, comando, kwargs):
        cherrypy.log("Yacare[_enviar_comando]: %s %s"%(comando, str(kwargs)))
        respuesta=''
        #
        url='/%s'%comando
        if len(kwargs)>0:
            url+='?%s'%up.urlencode(kwargs)
        url+='\n'
        #
        sckt=socket.socket()
        try:
            sckt.connect(('127.0.0.1', 8081))
            sckt.sendall(url.encode('utf-8'))
            while True:
                buffer=sckt.recv(1024)
                if not buffer: break
                respuesta+=buffer.decode('utf-8')
                if respuesta.endswith('\n'): break
        except Exception as e:
            cherrypy.log("Yacare[_enviar_comando]: %s"%str(e))
        finally:
            sckt.close()
        cherrypy.log("Yacare[_enviar_comando]: respuesta (%i) %s"%(len(respuesta), respuesta))
        return respuesta

if __name__=='__main__':
    print("main: iniciando...")
    #
    cherrypy.tree.mount(Yacare(), '/')
    cherrypy.engine.start()
    cherrypy.engine.block()
    print("main: terminado")
