#!/usr/bin/python3

import cherrypy
import multiprocessing
import subprocess
import tempfile
import os, os.path
import jinja2
import apiclient.discovery as ytapi

dir_media="/home/flaco/media"
yacare=None
salida=False
extensiones={
                    'musica':['mp3', 'wav', 'flac', 'ogg'], 
                    'video':['mkv', 'avi', 'mpg', 'mp4'], 
                    'subtitulos':['srt', 'sub']
                    }
ruta_input_fifo=os.path.join(tempfile.gettempdir(), "input_fifo")

class Reproduccion(multiprocessing.Process):
    
    def __init__(self, datos_entrada, ruta):
        multiprocessing.Process.__init__(self)
        self.datos_entrada=datos_entrada
        self.ruta=ruta
    
    def run(self):
        print("proceso de reproducción: %s %s"%(str(self.datos_entrada), self.ruta))
        #
        if os.path.exists(ruta_input_fifo): os.remove(ruta_input_fifo)
        os.mkfifo(ruta_input_fifo)
        #
        ruta_output=os.path.join(tempfile.gettempdir(), "output_fifo")
        if os.path.exists(ruta_output): os.remove(ruta_output)
        #
        tipo=self.datos_entrada['tipo']
        pc=None
        if tipo=='m' or tipo=='v':
            cmd='/usr/bin/mplayer -fs -input file=%(ruta_fifo)s "%(ruta)s"'%{'ruta_fifo':ruta_input_fifo, 'ruta':self.ruta}
            print("iniciando subprocess %s..."%cmd)
            pc=subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, close_fds=True)
            print("subprocess terminado")
            os.remove(ruta_input_fifo)
            with open(ruta_output, 'w') as outf:
                outf.write(pc.stdout.decode('utf-8'))
        elif tipo=='yt_video':
            yt_file=os.path.join(tempfile.gettempdir(), "yt_file")
            yt_url='https://www.youtube.com/watch?v=%s'%self.datos_entrada['id']
            if os.path.exists(yt_file):
                os.remove(yt_file)
            os.mkfifo(yt_file)
            cmd='/usr/bin/youtube-dl --no-part -o - %(yt_url)s > %(yt_file)s & mplayer -fs -input file=%(ruta_fifo)s %(yt_file)s'%{'ruta_fifo':ruta_input_fifo, 'yt_file':yt_file, 'yt_url':yt_url}
            print("iniciando subprocess %s..."%cmd)
            pc=subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, close_fds=True)
            print("subprocess terminado")
            os.remove(ruta_input_fifo)
            os.remove(yt_file)
        try :
            os.kill(pc.pid, 9)
            with open(ruta_output, 'w') as outf:
                outf.write(pc.stdout.decode('utf-8'))
        except:
            pass
        os.kill(self.pid, 12)
        os.kill(os.getppid(), 12)
        #
        print("proceso de reproducción terminado (%s)"%self.ruta)

class Yacare:
    
    def __init__(self):
        self.jjenv=jinja2.Environment(loader=jinja2.FileSystemLoader('./templates'), trim_blocks=True, lstrip_blocks=True)
        self.proceso=None
        self.id_entrada="0"
        self.lista=["número %i"%i for i in range(5)]
        self.lista_idx=0
        #
        self.lista_entradas_pendientes=[] # [ruta, ...]
        self.lista_entradas_reproducidas=[]
        self.lista_siguiente=False
        #
        if os.path.exists(ruta_input_fifo):
            os.remove(ruta_input_fifo)
        #
        self.yt=Yt(self.jjenv)
    
    @cherrypy.expose
    def index(self):
        template=self.jjenv.get_template("index.html")
        return template.render()
    
    @cherrypy.expose
    @cherrypy.popargs('tipo')
    @cherrypy.popargs('id_entrada')
    def reproducir(self, tipo, id_entrada):
        print("reproducir %s"%id_entrada)
        self.cmd('detener')
        datos=None
        ruta=''
        if tipo=='m' or tipo=='v':
            ruta=self._ruta_de_id_entrada(id_entrada)
            if ruta in self.lista_entradas_pendientes:
                self.lista_entradas_pendientes.remove(ruta)
                self.lista_entradas_reproducidas.append(ruta)
            datos=self._datos_entrada(ruta, id_entrada)
        elif tipo=='yt_video':
            datos={'id':id_entrada, 
                        'tipo':tipo, 
                        'etiqueta':'', 
                        'extension':''
                        }
        r=Reproduccion(datos, ruta)
        print("iniciar reproducción...")
        r.start()
        print("reproducción iniciada!")

    @cherrypy.expose
    @cherrypy.popargs('comando')
    def cmd(self, comando):
        print("cmd %s->%s"%(comando, ruta_input_fifo))
        cmddata=None
        if comando=='detener':
            cmddata='stop\n'
            self.lista_siguiente=False
        elif comando=='siguiente':
            cmddata='stop\n'
            self.lista_siguiente=True
        if os.path.exists(ruta_input_fifo):
            with open(ruta_input_fifo, 'wb', 0) as fifo:
                fifo.write(cmddata.encode('utf-8'))

    @cherrypy.expose
    @cherrypy.popargs('tipo')
    @cherrypy.popargs('id_entrada')
    def lista_agregar(self, id_entrada):
        ruta=self._ruta_de_id_entrada(id_entrada)
        if not ruta in self.lista_entradas_pendientes:
            self.lista_entradas_pendientes.append(ruta)

    @cherrypy.expose
    def lista_reproduccion(self):
        datos_entradas=[]
        for ruta in self.lista_entradas_pendientes:
            id_entrada=self._id_de_ruta(ruta)
            datos_entrada=self._datos_entrada(ruta, id_entrada)
            datos_entradas.append(datos_entrada)
        template=self.jjenv.get_template('lista_reproduccion.html')
        return template.render(lista=datos_entradas)

    @cherrypy.expose
    @cherrypy.popargs('id_entrada')
    def listar_dir(self, id_entrada=None):
        if id_entrada!=None:
            self.id_entrada=id_entrada
        id_padre=self._id_entrada_padre(self.id_entrada)
        datos_entradas=[]
        ruta=self._ruta_de_id_entrada(self.id_entrada)
        entradas=[os.path.join(ruta, entrada) for entrada in os.listdir(ruta)]
        for i in range(len(entradas)):
            entrada=entradas[i]
            #print(entrada)
            datos_entrada=self._datos_entrada(entrada, "_".join([self.id_entrada, str(i)]))
            if not datos_entrada['tipo']=='n':
                datos_entradas.append(datos_entrada)
        datos_entradas.sort(key=lambda x:x['etiqueta'].lower())
        template=self.jjenv.get_template("listar_dir.html")
        return template.render(id_entrada_padre=id_padre, ruta_dir=ruta, lista=datos_entradas)
    
    def lista_reproducir_siguiente(self):
        if len(self.lista_entradas_pendientes)>0 and self.lista_siguiente:
            ruta=self.lista_entradas_pendientes.pop(0)
            self.lista_entradas_reproducidas.append(ruta)
            id_entrada=self._id_de_ruta(ruta)
            datos=self._datos_entrada(ruta, id_entrada)
            r=Reproduccion(datos, ruta)
            r.start()
        else:
            for ruta in self.lista_entradas_reproducidas:
                self.lista_entradas_pendientes.append(ruta)
            self.lista_entradas_pendientes.clear()
    
    def _id_entrada_padre(self, id_entrada):
        if id_entrada==None:
            return ''
        idp, sep, idx=id_entrada.rpartition("_")
        return idp
    
    def _ruta_de_id_entrada(self, id_entrada):
        ruta=dir_media
        if id_entrada!="0":
            partes_id=id_entrada.split("_")
            partes_id.pop(0)
            for parte_id in partes_id:
                idx_entrada=int(parte_id)
                entradas=os.listdir(ruta)
                entrada=entradas[idx_entrada]
                ruta=os.path.join(ruta, entrada)
        return ruta
    
    def _id_de_ruta(self, ruta):
        print("_id_de_ruta: %s"%ruta)
        if not os.path.exists(ruta):
            return ''
        if not ruta.startswith(dir_media):
            return ''
        subdirs=ruta[len(dir_media):]
        print("_id_de_ruta subdirs %s"%subdirs)
        if subdirs=='':
            return '0'
        partes_subdirs=subdirs.split('/')
        print("_id_de_ruta partes_subdirs %s"%str(partes_subdirs))
        indices=[0]
        ruta_parcial=dir_media
        for parte in partes_subdirs:
            if parte=='': continue
            entradas=os.listdir(ruta_parcial)
            indice=entradas.index(parte)
            indices.append(indice)
            ruta_parcial=os.path.join(ruta_parcial, parte)
        id_entrada="_".join([str(i) for i in indices])
        print("_id_de_ruta id_entrada %s"%id_entrada)
        return id_entrada
        
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
        if extension in extensiones['musica']:
            tipo='m'
        elif extension in extensiones['video']:
            tipo='v'
        elif extension in extensiones['subtitulos']:
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

class Yt:
    
    def __init__(self, jjenv):
        self.jjenv=jjenv
        #
        self.DEVELOPER_KEY = "AIzaSyCfflFDLE_k0rRxzEO44eDSgkodDfOwF6Y"
        self.YOUTUBE_API_SERVICE_NAME = "youtube"
        self.YOUTUBE_API_VERSION = "v3"
    
    @cherrypy.expose
    def index(self, c=None):
        _entradas=self._buscar(c)
        template=self.jjenv.get_template("yt.html")
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
        
def sigint():
    global salida
    print("sigint!")
#    salida=True
    cherrypy.engine.stop()
    cherrypy.engine.exit()
    print("sigint terminado")

def sigusr2():
    global yacare
    print("sigusr2!")
    yacare.lista_reproducir_siguiente()
    print("sigusr2 terminado")

if __name__=='__main__':
    print("main: comienza...")
    yacare=Yacare()
    cherrypy.engine.signal_handler.subscribe()
    cherrypy.engine.signal_handler.set_handler(2, sigint)
    cherrypy.engine.signal_handler.set_handler(12, sigusr2)
    cherrypy.engine.autoreload.subscribe()
    cherrypy.config.update("yacare.conf")
    cherrypy.tree.mount(yacare, "/")
    cherrypy.engine.start()
    cherrypy.engine.block()
    print("main: termina")
    
