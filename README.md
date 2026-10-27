# Perussi Advogados: site + CRM

Site institucional do escritório Perussi Advogados (Londrina - PR) com um CRM básico em `/admin`.

## Funcionalidades
- **Site**: hero, áreas de atuação, seção "Quem sou", como funciona, contato (formulário + WhatsApp + mapa), política de privacidade (LGPD), SEO local (schema.org `LegalService`).
- **CRM** (`/admin`, login único):
  - **Leads**: o formulário do site cai aqui; funil Novo → Em contato → Consulta agendada → Virou cliente / Perdido; conversão em cliente com um clique.
  - **Clientes** com busca e processos vinculados.
  - **Processos** com honorários combinados/recebidos e **consulta ao Datajud (CNJ)**: classe, vara, assuntos e movimentações. "Atualizar todos" marca os processos com movimentação nova, que aparecem no painel.
  - **Agenda** de audiências, prazos e tarefas, com alerta de atrasados.

## Rodar localmente
```bash
pip install -r requirements.txt
ADMIN_PASSWORD=minhasenha python app.py
```
Acesse http://localhost:5000 e http://localhost:5000/admin (usuário `paulo`).

## Configuração (variáveis de ambiente)
Veja `.env.example`: `SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`, `OAB_NUMERO`, `DATABASE`, `DATAJUD_API_KEY` (opcional).

## Foto do Paulo
Coloque a foto em `static/img/paulo.jpg` (ou .png/.webp), de preferência vertical 4:5. Sem ela, o logo aparece no lugar.

## Produção
`gunicorn app:app`. Use um servidor com disco persistente (Render, Railway, VPS) porque o banco é SQLite em `instance/crm.db`, e faça backup desse arquivo.
