# Bot de Disparos — Telegram

Painel web para **programar o envio de mensagens** (texto, foto ou vídeo) em
**grupos e canais** do Telegram, com agendamento único, diário ou semanal.

## O que faz

- Painel web local para criar, listar e cancelar disparos
- Envia **texto**, **foto** (com legenda) e **vídeo** (com legenda)
- Agendamento **único**, **diário** ou **semanal**
- Persistência: os agendamentos sobrevivem a reinícios do programa
- Botão para **descobrir os IDs** dos grupos/canais onde o bot está

## Como configurar (passo a passo)

### 1. Criar o bot no Telegram
1. No Telegram, fale com o **@BotFather**.
2. Envie `/newbot`, escolha um nome e um usuário para o bot.
3. Copie o **token** que ele te dá (algo como `123456:ABC-...`).

### 2. Adicionar o bot ao grupo/canal
- **Grupo:** adicione o bot ao grupo.
- **Canal:** adicione o bot como **administrador** do canal (com permissão de publicar).

### 3. Instalar o projeto
```powershell
cd "C:\Users\Tiago Marques\Desktop\bot-disparos"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Abra o arquivo `.env` e cole o seu token em `TELEGRAM_BOT_TOKEN`.

### 4. Rodar
```powershell
python app.py
```
Abra no navegador: http://127.0.0.1:5000

## Como usar

1. No painel, clique em **🔍 Descobrir grupos/canais** para pegar o ID do destino
   (mande uma mensagem no grupo antes, ou publique algo no canal, para ele aparecer).
2. Escolha o tipo (texto / foto / vídeo), escreva o conteúdo ou faça upload.
3. Defina **data**, **hora** e a **repetição**.
4. Clique em **Agendar disparo**.

> **Importante:** o programa (`python app.py`) precisa estar **rodando** na hora
> agendada para o envio acontecer. Se o PC estiver desligado no horário exato,
> há uma tolerância de 1h; para envios 24/7 use um servidor sempre ligado.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Painel web (Flask) e rotas |
| `scheduler.py` | Agendador (APScheduler) e envio na hora certa |
| `telegram_api.py` | Chamadas à Bot API do Telegram |
| `db.py` | Banco SQLite dos disparos |
| `config.py` | Configurações lidas do `.env` |
| `templates/index.html` | Interface do painel |
