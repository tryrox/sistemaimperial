# Chancelaria Imperial de Solitude

Sistema web em português, responsivo, com HUD escura inspirada na organização do Linear, ícones vetoriais consistentes e detalhes imperiais discretos. Python 3.12+ e SQLite, sem dependências externas.

## Abrir localmente no Windows

Instale Python 3.12+ com a opção **Add Python to PATH**, baixe e extraia o repositório e abra `iniciar-local.bat`. Acesse http://localhost:8000 com usuário `admin` e senha inicial `ImperialLocal2026`. Mantenha o terminal aberto. Os dados locais ficam em `data/local.db`; este arquivo não é enviado ao GitHub. Essa credencial é exclusiva para testes locais. Não use o iniciador em hospedagem pública. A senha inicial só funciona quando esse banco ainda não possui usuários.

## Executar

```bash
export ADMIN_NAME=admin
export ADMIN_PASSWORD='defina-uma-senha-exclusiva-com-12-ou-mais-caracteres'
python server.py
```

Abra http://localhost:8000 e entre com os dados definidos. As variáveis devem ser configuradas no ambiente; `.env.example` é somente uma referência, não é carregado automaticamente. A senha inicial só é usada para criar o primeiro administrador. Não há senha padrão. O sistema começa vazio, sem dados fictícios.

## Interface

- Navegação agrupada por workspace, administração, relações e arquivo.
- Tema escuro em todas as telas, login e formulários.
- Paleta de comandos com `Ctrl+K` (ou `Cmd+K`), busca e navegação por setas/Enter.
- Painel com pendências reais, agenda, publicações e atividade recente.
- Indicadores clicáveis e filtro por situação nas listagens.
- Layout responsivo e respeito à preferência de movimento reduzido.

## Módulos

- Visão geral: indicadores calculados, últimos decretos e auditoria.
- Cidadãos: ficha, origem, URL de retrato e funções acumuladas.
- Legião: integrante, patente, divisão, responsável, histórico de promoções e relatórios em texto.
- Magos de Batalha: integrantes, escolas e operações em texto.
- Diplomacia: territórios, Emissário e Aprendiz de Emissário.
- Contratos e tratados: partes, signatários, vigência, situação e texto.
- Tesouraria: entradas e saídas de septins, saldo calculado.
- Suprimentos: movimentações com quantidade e unidade; consulta por item na busca.
- Decretos e convocações: publicação, responsável, local e data.
- Mapa Imperial: área reservada, sem mapa implementado. Integração HTML futura em `public/app.js`, seção `map`. A política CSP restringe frames à própria origem; revisar conscientemente ao integrar um provedor externo.
- Acessos: administrador cria e edita usuários com nome, senha e múltiplos cargos.

Todos os módulos permitem criar, consultar, editar, excluir e pesquisar registros conforme as permissões. As fichas de cidadãos não concedem permissões: os cargos de acesso são atribuídos separadamente na criação de usuários. Recuperação automática de senha, upload de arquivos, assinaturas digitais e fluxos formais de aprovação ainda não estão implementados. Retratos são armazenados como URL; a listagem inicial não os exibe.

## Autoridade e permissões

Rei → Jarl de Solitude → General. Capitães e Magos de Batalha integram a estrutura militar. Emissários e seus aprendizes pertencem à esfera diplomática.

| Cargo | Escrita |
|---|---|
| Administrador, Rei, Jarl de Solitude | Todos os módulos e acessos |
| General | Legião, Magos, Diplomacia, Tratados, Convocações |
| Capitão | Legião e Convocações |
| Mago de Batalha | Magos |
| Emissário | Diplomacia e Tratados |
| Tesoureiro | Tesouraria e Suprimentos |
| Demais cargos | Consulta |

Permissões são cumulativas e verificadas no servidor. Todos os usuários autenticados podem consultar todos os registros operacionais e as últimas 20 atividades; não existem documentos sigilosos nesta versão. O General pode registrar a oficialização diplomática, mas isso não coloca os Emissários na cadeia militar.

## Hospedagem e dados

Use um host com Python ou Docker e disco persistente. Vercel e GitHub Pages não executam este servidor SQLite persistente. Configure `PORT` conforme o host. Em produção, use proxy HTTPS e `COOKIE_SECURE=1`. No Docker, monte volume em `/app/data` com permissão para o usuário `imperial` gravar. O banco fica em `DATABASE_PATH`; faça backups regulares com a API SQLite backup ou com o servidor parado. Não envie banco ou credenciais ao GitHub.

Senhas com PBKDF2-SHA256, sessões HttpOnly/SameSite com expiração de 12 horas, limitação de tentativas de login por IP, validação de mutações e auditoria. O limitador de tentativas é local ao processo. Não exponha diretamente à internet sem proxy HTTPS. Não há integração Discord ou Supabase configurada.

## Verificar

```bash
python -m unittest discover -s tests -v
node --check public/app.js
```
