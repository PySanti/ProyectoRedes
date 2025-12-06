import socket
import tkinter as tk
from tkinter import ttk, scrolledtext
from urllib.parse import urlparse
import threading
import ssl

class HTTPClient:
    """Clase encargada de la lógica de red y protocolo HTTP"""
    
    def request(self, url, method="GET", max_redirects=5):
        current_url = url
        redirects_count = 0

        while redirects_count < max_redirects:
            try:
                # 1. Parsear la URL
                parsed = urlparse(current_url)
                host = parsed.hostname
                path = parsed.path if parsed.path else "/"
                if parsed.query:
                    path += "?" + parsed.query
                
                # Definir puerto y esquema (http/https)
                scheme = parsed.scheme
                port = parsed.port
                if not port:
                    port = 443 if scheme == "https" else 80

                # 2. Crear Socket TCP
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)

                # Manejo de HTTPS usando SSL
                if scheme == "https":
                    context = ssl.create_default_context()
                    sock = context.wrap_socket(sock, server_hostname=host)

                # 3. Conectar
                sock.connect((host, port))

                # 4. Construir Headers obligatorios
                request_line = f"{method} {path} HTTP/1.1\r\n"
                headers = f"Host: {host}\r\n"
                headers += "User-Agent: ClienteHTTP-Alterno/1.0\r\n"
                headers += "Connection: close\r\n"
                headers += "\r\n"

                # 5. Enviar Solicitud
                full_request = request_line + headers
                sock.sendall(full_request.encode('utf-8'))

                # 6. Recibir Respuesta
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                
                sock.close()

                # 7. Separar Cabeceras y Cuerpo
                parts = response.split(b"\r\n\r\n", 1)
                header_bytes = parts[0]
                body_bytes = parts[1] if len(parts) > 1 else b""

                header_text = header_bytes.decode('utf-8', errors='replace')
                body_text = body_bytes.decode('utf-8', errors='replace')

                # 8. Analizar Status Code
                first_line = header_text.splitlines()[0]
                status_code = int(first_line.split(" ")[1])

                # 9. Lógica de Redirección (3xx)
                if status_code in [301, 302, 303, 307, 308]:
                    new_location = None
                    for line in header_text.splitlines():
                        if line.lower().startswith("location:"):
                            new_location = line.split(":", 1)[1].strip()
                            break
                    
                    if new_location:
                        redirects_count += 1
                        # Manejo de URLs relativas
                        if not new_location.startswith("http"):
                            current_url = f"{scheme}://{host}{new_location}"
                        else:
                            current_url = new_location
                        continue # Repetir el bucle

                # Si no es redirección, retornamos resultado
                return first_line, header_text, body_text

            except Exception as e:
                return "Error", f"Ocurrió una excepción: {str(e)}\n\nIntentando URL: {current_url}", ""
        
        return "Error", f"Demasiadas redirecciones ({max_redirects}) alcanzadas.", ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Proyecto de Redes de comunicación de datos: Cliente para navegación web sencilla")
        self.geometry("1000x700")
        self.configure(bg="#f0f0f0")
        
        self.client = HTTPClient()

        self.create_widgets()

    def create_widgets(self):
        # Este es el frame principal
        control_frame = tk.Frame(self, bg="#dcdcdc", padx=10, pady=10)
        control_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Input de URL
        tk.Label(control_frame, text="URL:", bg="#dcdcdc", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = tk.Entry(control_frame, width=60, font=("Arial", 10))
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.url_entry.insert(0, "http://ucab.edu.ve")

        # Esta es la seccion de seleccion de Método
        tk.Label(control_frame, text="Método:", bg="#dcdcdc", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        self.method_var = tk.StringVar(value="GET")
        methods = ["GET", "HEAD"]
        self.method_menu = ttk.OptionMenu(control_frame, self.method_var, "GET", *methods)
        self.method_menu.pack(side=tk.LEFT, padx=5)

        # Botón Enviar
        self.send_btn = tk.Button(control_frame, 
                                  text="Enviar Solicitud", 
                                  command=self.start_request, # metodo que se ejecutara al presionar el boton, definido mas abajo
                                  bg="#4CAF50", 
                                  fg="white", 
                                  font=("Arial", 10, "bold"))
        self.send_btn.pack(side=tk.RIGHT, padx=(15, 0))

        # Este es el frame de resultados, el que esta dividido verticalmente
        results_frame = tk.Frame(self, bg="#f0f0f0")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # El frame de las cabeceras
        left_frame = tk.Frame(results_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="Cabeceras de Respuesta:", anchor="w", font=("Arial", 12, "bold")).pack(fill=tk.X, pady=(0, 3))
        self.headers_text = scrolledtext.ScrolledText(left_frame, height=1, width=1, font=("Consolas", 9), wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=2)
        self.headers_text.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)


        # El frame del body
        right_frame = tk.Frame(results_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(right_frame, text="Cuerpo / Contenido HTML:", anchor="w", font=("Arial", 12, "bold")).pack(fill=tk.X, pady=(0, 3))
        self.body_text = scrolledtext.ScrolledText(right_frame, height=1, width=1, font=("Consolas", 9), wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=2)
        self.body_text.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)


    def start_request(self):
        """Inicia la petición en un hilo separado para no congelar la GUI"""
        url = self.url_entry.get()
        method = self.method_var.get()
        
        # Limpiar campos y mostrar estado
        self.headers_text.delete(1.0, tk.END)
        self.body_text.delete(1.0, tk.END)
        self.headers_text.insert(tk.END, "Iniciando conexión...\n")
        self.send_btn.config(state=tk.DISABLED, text="Conectando...")

        # Usar threading para que la interfaz no se congele
        thread = threading.Thread(target=self.run_request, args=(url, method))
        thread.start()

    def run_request(self, url, method):
        if not url.startswith("http"):
            url = "http://" + url
            
        status_line, headers, body = self.client.request(url, method)

        # Actualizar GUI
        self.headers_text.delete(1.0, tk.END)
        self.body_text.delete(1.0, tk.END)

        if status_line == "Error":
            self.headers_text.insert(tk.END, "ERROR DE CONEXIÓN O PROTOCOLO\n\n")
            self.body_text.insert(tk.END, headers) # headers contiene el mensaje de error
        elif method == "HEAD":
            self.headers_text.insert(tk.END, status_line + "\n" + headers)
            self.body_text.insert(tk.END, "[El método HEAD solo recupera cabeceras, el cuerpo está vacío]")
        else:
            self.headers_text.insert(tk.END, status_line + "\n" + headers)
            self.body_text.insert(tk.END, body)

        # Restaurar botón
        self.send_btn.config(state=tk.NORMAL, text="Enviar Solicitud")


if __name__ == "__main__":
    app = App()
    app.mainloop()
