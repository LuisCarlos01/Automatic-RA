# 🤖 Reclame Aqui Bot – Sistema Automatizado com IA

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=for-the-badge&logo=openai&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-Automation-43B02A?style=for-the-badge&logo=selenium&logoColor=white)

**Reclame Aqui Bot** é um sistema automatizado que processa e responde reclamações na plataforma **Reclame Aqui**, utilizando inteligência artificial para gerar respostas personalizadas e enviá-las automaticamente.

---

## 📌 Recursos Principais

- 🔐 Login automatizado na conta do Reclame Aqui
- 🔍 Varredura e leitura de novas reclamações
- 🤖 Geração de respostas com IA via OpenAI
- 📤 Envio automático de respostas diretamente para a plataforma
- 🗃️ Banco de dados local com SQLite para controle de reclamações e respostas enviadas
- ⏰ Verificações periódicas com agendamento customizável

---

## 🧰 Tecnologias Utilizadas

- **Linguagem**: Python 3.x
- **Automação de Navegador**: Selenium
- **Inteligência Artificial**: API OpenAI (GPT)
- **Banco de Dados Local**: SQLite
- **Agendamentos**: Cron/Agendador interno

---

## 🛠️ Instalação

1. Clone este repositório:

```bash
git clone https://github.com/LuisCarlos01/reclameaqui-bot.git
cd reclameaqui-bot
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Configure suas variáveis de ambiente no `.env`:

```env
OPENAI_API_KEY=sk-...
RA_EMAIL=seu_email@exemplo.com
RA_PASSWORD=sua_senha
CHECK_INTERVAL_MINUTES=30
```

---

## ▶️ Como Executar

```bash
python bot.py
```

O sistema iniciará o processo de login, leitura de novas reclamações e envio de respostas.

---

## 📂 Estrutura do Projeto

```
/
├── bot.py              # Script principal de automação
├── resposta_ia.py      # Geração de resposta com OpenAI
├── database.py         # Módulo de banco de dados SQLite
├── agendador.py        # Agendamento de tarefas
├── .env                # Variáveis de ambiente
└── requirements.txt    # Dependências do projeto
```

---

## 💡 Sugestões de Uso

- Ideal para equipes de atendimento que recebem grande volume de reclamações
- Pode ser adaptado para outras plataformas com automação de navegador
- Possui potencial de integração com dashboards ou sistemas de CRM

---

## 👨‍💻 Desenvolvido por

Feito com dedicação por **Luis Carlos**  
[GitHub](https://github.com/LuisCarlos01) | [LinkedIn](https://www.linkedin.com/in/luizcarloss/)

---

## 📄 Licença

Este projeto está sob a licença MIT.
