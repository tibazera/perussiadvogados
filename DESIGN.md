# Design: Perussi Advogados

Escritório clássico executado com rigor. O advogado tem rosto, nome e OAB.

## Cores
| Token | Valor | Uso |
|---|---|---|
| `--navy` | #0f1f3a | campos inteiros (abertura, contato), títulos, botões primários |
| `--navy-deep` | #0a1629 | faixa de credenciais, rodapé |
| `--gold` | #b8955a | fios, ícones, botão de envio (só sobre marinho ou como fundo) |
| `--gold-light` | #d9bf8c | destaque de texto sobre marinho, seleção |
| `--gold-ink` | #85652f | dourado para texto sobre fundo claro (contraste AA) |
| `--mist` | #f3f5f8 | seções alternadas (Quem sou, Dúvidas) |
| `--paper` | #ffffff | fundo de leitura |
| WhatsApp | #137a40 | botão flutuante |

Estratégia: marinho comprometido em grandes campos; dourado nunca como texto sobre branco (use `--gold-ink`).

## Tipografia (self-hosted em `static/fonts/`)
- Títulos: **Libre Caslon Display** 400, eco das capitulares do logo. Hero até 4.6rem, seções 2.1–3.3rem.
- Citação: Libre Caslon Text itálico, só no blockquote.
- Texto e interface: **Source Sans 3** 400/600/700, corpo 1.0625rem/1.65.

## Logo
- `static/img/logo-navy.png` e `logo-branco.png`: wordmark transparente, recortado do original `perussi_01_preto_branco.png`. Cabeçalho a 52px de altura (42px no celular), rodapé a 44px.

## Componentes
- Botões retos (raio 2px): `btn-navy`, `btn-gold`, `btn-line`.
- Listas editoriais com fios de 1px (áreas, FAQ, canais), sem cards iguais.
- Painel "Qual é a sua situação?": opções que abrem o WhatsApp com mensagem pré-preenchida.
- Ícones SVG de traço 1.6 em `templates/_icones.html`.

## Movimento
Uma única entrada na abertura (subida + desfoque, ease-out exponencial), respeitando `prefers-reduced-motion`. Microinterações: sublinhado dourado no menu, deslocamento da seta nas opções.

## Regras
Sem rótulo acima dos títulos, sem gradiente em texto, sem sombras decorativas além do painel da abertura. Nome e OAB visíveis (Provimento 205/2021).
