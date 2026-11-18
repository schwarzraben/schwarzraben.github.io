# Automação Steel: Excel → WhatsApp Business

Você coloca os leads na planilha e o script manda a primeira mensagem pelo
número da Steel, usando a **API oficial do WhatsApp Business (Meta Cloud API)**.
O número não corre risco de banimento por usar ferramenta não oficial.

## 1. Configuração (uma vez só)

1. Acesse **developers.facebook.com** → *Criar app* → tipo **Empresa** → adicione o produto **WhatsApp**.
2. Em *WhatsApp → Configuração da API*, adicione o número da Steel e confirme por SMS.
   - O número **não pode** estar em uso no app do WhatsApp comum ao mesmo tempo. Use um número dedicado ou migre.
3. Copie o **ID do número de telefone** (Phone number ID).
4. Gere um **token permanente**: *Configurações do negócio → Usuários do sistema → Gerar token*
   com as permissões `whatsapp_business_messaging` e `whatsapp_business_management`.
5. Cadastre um cartão em *Pagamentos*. A Meta cobra por conversa iniciada pela empresa.

## 2. Criar o modelo de mensagem (template)

A primeira mensagem para um lead **precisa** ser um template aprovado pela Meta.
Em *WhatsApp Manager → Modelos de mensagem → Criar*:

- **Nome:** `steel_primeiro_contato`
- **Categoria:** Marketing
- **Idioma:** Português (BR)
- **Corpo** (o `{{1}}` vira o primeiro nome do lead):

```
Oi, {{1}}! Aqui é da Steel Design 👋
Obrigado pelo seu interesse. Separamos uma análise rápida do visual da sua marca
(Instagram, posts e identidade). Posso te mandar por aqui?
```

- **Botões de resposta rápida:** `Quero ver` · `Agora não`

A aprovação leva de minutos a 24 h.

## 3. Instalação no computador

Precisa do Python 3.9+ instalado.

```bash
pip install -r requirements.txt
cp .env.exemplo .env        # depois edite o .env com o token e o ID
cp leads_modelo.xlsx leads.xlsx
```

## 4. Uso no dia a dia

1. Abra o `leads.xlsx` e preencha uma linha por lead:

| coluna | o que colocar |
|---|---|
| nome | nome do lead |
| telefone | qualquer formato: `(11) 98765-4321`, `11987654321`, `+55 11 ...` |
| empresa / instagram / origem | opcional, para controle seu |
| consentimento | **SIM** só se a pessoa autorizou contato (formulário, mensagem, cartão etc.) |
| status, data_envio, detalhe | deixe em branco: o script preenche |

2. Feche o Excel e rode primeiro em modo teste:

```bash
python enviar.py --teste
```

3. Se estiver tudo certo, rode de verdade:

```bash
python enviar.py
```

### O que o script faz sozinho
- Corrige o formato do telefone (coloca o 55 e tira símbolos).
- Pula quem já recebeu (`enviado`), quem é `cliente`, quem pediu para sair (`descadastrado`), quem não tem consentimento, telefones inválidos e duplicados.
- Grava na planilha o status, a data e o ID da mensagem ou o erro, salvando a cada envio.
- Espera 8 s entre envios e para em 30 por execução (mude com `--limite` e `--intervalo`).
- Interrompe tudo se o token for inválido ou se a Meta avisar sobre limite ou qualidade do número.

### Quando o lead responder
As respostas chegam na **Caixa de entrada do WhatsApp Business** (Meta Business Suite).
Depois de ele responder, você tem 24 h para conversar livremente.
Atualize o status na planilha: `respondeu`, `cliente` ou `descadastrado` (se pedir para parar).

## Cuidados para não perder o número
- Envie só para quem tem **consentimento = SIM**. Muitos bloqueios derrubam a qualidade do número.
- Comece com poucos envios por dia. A Meta libera limites maiores conforme a qualidade.
- Nunca compartilhe o arquivo `.env` (é a senha do número) nem a planilha com dados reais.
