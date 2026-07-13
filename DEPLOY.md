# Deploy na VPS — Extrator de Importação (Aconsult, mockup)

> **Mockup, não produção.** O objetivo é publicar o app numa VPS com URL própria para
> a Larissa testar extração/exportação (spec §13, Fatia 1, item "Empacotar para VPS").
> **Não** há autenticação nem TLS embutidos. Coloque atrás da **VPN da empresa** ou de
> um **basic auth** no nginx, e ative **HTTPS** (ex.: Let's Encrypt/Certbot) antes de
> divulgar a URL. Sem banco/persistência: a Relação das Importações (Saída D) usa o
> padrão *upload → append → download* (a persistência é o arquivo da própria empresa).

O app é FastAPI (ASGI) — objeto `backend.main:app`. Serve a API e o front-end estático.
As dependências estão **pinadas** em `requirements.txt` (spec §13) para reproduzir na VPS
exatamente o ambiente validado contra o corpus real; **não** repinar sem rodar `pytest`.

Comando de produção (referência, usado nas duas opções abaixo — **sem `--reload`**):

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## Opção A — Docker (mais simples)

```bash
# na raiz do projeto (onde está o Dockerfile)
docker build -t aconsult-extrator .
docker run -d --name aconsult-extrator --restart unless-stopped \
  -p 8000:8000 aconsult-extrator
```

- App em `http://SEU_IP:8000/`. Trocar a porta interna: `-e PORT=9000` (o uvicorn lê `$PORT`).
- Logs: `docker logs -f aconsult-extrator`. Atualizar: `docker build` + `docker rm -f` + `docker run` de novo.
- Um worker atende bem o mockup. Para escalar, edite o `CMD` do Dockerfile com `--workers N`
  (o app não tem estado em memória).
- **Coloque um nginx/Caddy na frente** para TLS e `client_max_body_size` (ver bloco nginx abaixo);
  o `-p 8000:8000` exposto direto é só para teste local.

---

## Opção B — systemd + nginx (bare metal / sem Docker)

### 1. Preparar o app e o virtualenv

```bash
sudo useradd -r -m -d /opt/aconsult-extrator aconsult   # usuário de serviço, sem shell de login
sudo -u aconsult -H bash -c '
  cd /opt/aconsult-extrator
  git clone <repo> app            # ou copie os arquivos para /opt/aconsult-extrator/app
  python3.11 -m venv venv
  ./venv/bin/pip install --upgrade pip
  ./venv/bin/pip install -r app/requirements.txt   # deps pinadas: build reproduzível
'
```

### 2. Unit do systemd — `/etc/systemd/system/aconsult-extrator.service`

```ini
[Unit]
Description=Extrator de Importacao - Aconsult (mockup)
After=network.target

[Service]
Type=simple
User=aconsult
Group=aconsult
WorkingDirectory=/opt/aconsult-extrator/app
Environment=PORT=8000
# ASGI de producao: SEM --reload. Um worker basta; escalar com --workers N.
ExecStart=/opt/aconsult-extrator/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> Bind em `127.0.0.1`: quem fica exposto na internet é o nginx, não o uvicorn.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aconsult-extrator
sudo systemctl status aconsult-extrator     # conferir; logs: journalctl -u aconsult-extrator -f
```

### 3. Reverse proxy nginx — ex.: `/etc/nginx/sites-available/aconsult-extrator`

```nginx
server {
    listen 80;
    server_name extrator.suaempresa.com.br;   # ajuste

    # PDFs podem ter vários MB; alinhe com o limite de upload do app (25 MB).
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # extração de vários PDFs pode demorar
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/aconsult-extrator /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Depois: TLS com `sudo certbot --nginx -d extrator.suaempresa.com.br` e, se não for usar VPN,
um `auth_basic` no bloco `location /`.

---

## Limite de upload no app (defesa em profundidade)

O `client_max_body_size` do nginx corta uploads grandes na borda. Para o app também recusar
requisições acima do limite (útil no Docker sem proxy, ou se o proxy for reconfigurado), há um
middleware leve que responde **HTTP 413** quando o `Content-Length` passa de ~25 MB — ver o
trecho a aplicar em `backend/main.py`. Mantenha os dois limites (nginx e app) alinhados.

## Checagem de aceite

```bash
# Docker
docker build -t aconsult-extrator .
docker run --rm -p 8000:8000 aconsult-extrator &
curl -sf -o /dev/null -w '%{http_code}\n' http://localhost:8000/   # espera 200
```
