#!/usr/bin/env python3
"""
Automação Still: planilha de leads (Excel) -> WhatsApp Business (API oficial da Meta).

Uso:
  python enviar.py                  # envia para os leads pendentes
  python enviar.py --teste          # simula, não envia nada
  python enviar.py --planilha outra.xlsx --limite 50
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime

import requests
from openpyxl import load_workbook

API_VERSION = "v21.0"
COLUNAS = ["nome", "telefone", "empresa", "consentimento", "status", "data_envio", "detalhe"]


def carregar_env(caminho=".env"):
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def normalizar_telefone(bruto):
    """Converte '(11) 98765-4321' em '5511987654321'. Retorna None se inválido."""
    digitos = re.sub(r"\D", "", str(bruto or ""))
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) in (10, 11):          # DDD + número, sem país
        digitos = "55" + digitos
    if not (digitos.startswith("55") and len(digitos) in (12, 13)):
        return None
    return digitos


def primeiro_nome(nome):
    nome = str(nome or "").strip()
    return nome.split()[0].capitalize() if nome else "tudo bem"


def enviar_template(token, phone_id, telefone, template, idioma, variaveis):
    url = f"https://graph.facebook.com/{API_VERSION}/{phone_id}/messages"
    corpo = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {"name": template, "language": {"code": idioma}},
    }
    if variaveis:
        corpo["template"]["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": v} for v in variaveis],
        }]
    r = requests.post(url, json=corpo, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    dados = r.json() if r.content else {}
    if r.ok:
        return True, dados.get("messages", [{}])[0].get("id", "")
    erro = dados.get("error", {})
    return False, f"{erro.get('code', r.status_code)}: {erro.get('message', r.text)[:200]}"


def main():
    p = argparse.ArgumentParser(description="Envia mensagens de WhatsApp para leads da planilha.")
    p.add_argument("--planilha", default="leads.xlsx")
    p.add_argument("--limite", type=int, default=int(os.getenv("LIMITE_POR_EXECUCAO", "0") or 0) or 30)
    p.add_argument("--intervalo", type=float, default=8.0, help="segundos entre envios")
    p.add_argument("--teste", action="store_true", help="simula sem enviar")
    args = p.parse_args()

    carregar_env()
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    template = os.getenv("WHATSAPP_TEMPLATE", "still_primeiro_contato")
    idioma = os.getenv("WHATSAPP_TEMPLATE_IDIOMA", "pt_BR")
    if not args.teste and not (token and phone_id):
        sys.exit("Configure WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID no arquivo .env (veja .env.exemplo).")

    wb = load_workbook(args.planilha)
    ws = wb["Leads"] if "Leads" in wb.sheetnames else wb.active
    cab = [str(c.value or "").strip().lower() for c in ws[1]]
    for col in COLUNAS:
        if col not in cab:
            cab.append(col)
            ws.cell(row=1, column=len(cab), value=col)
    idx = {nome: i + 1 for i, nome in enumerate(cab)}

    def cel(linha, col):
        return ws.cell(row=linha, column=idx[col])

    enviados, pulados, erros = 0, 0, 0
    vistos = set()
    for linha in range(2, ws.max_row + 1):
        nome = cel(linha, "nome").value
        tel_bruto = cel(linha, "telefone").value
        if not nome and not tel_bruto and not cel(linha, "empresa").value:
            continue
        status = str(cel(linha, "status").value or "").strip().lower()
        if status in ("enviado", "descadastrado", "cliente"):
            continue
        if str(cel(linha, "consentimento").value or "").strip().lower() not in ("sim", "s", "yes", "x"):
            cel(linha, "status").value = "sem consentimento"
            pulados += 1
            continue
        tel = normalizar_telefone(tel_bruto)
        if not tel:
            cel(linha, "status").value = "telefone inválido"
            pulados += 1
            continue
        if tel in vistos:
            cel(linha, "status").value = "duplicado"
            pulados += 1
            continue
        vistos.add(tel)
        if enviados >= args.limite:
            break

        variaveis = [primeiro_nome(nome)]
        if args.teste:
            print(f"[TESTE] {tel} <- template '{template}' {variaveis}")
            enviados += 1
            continue

        ok, detalhe = enviar_template(token, phone_id, tel, template, idioma, variaveis)
        cel(linha, "data_envio").value = datetime.now().strftime("%d/%m/%Y %H:%M")
        cel(linha, "detalhe").value = detalhe
        if ok:
            cel(linha, "status").value = "enviado"
            enviados += 1
            print(f"OK   {tel} ({nome})")
        else:
            cel(linha, "status").value = "erro"
            erros += 1
            print(f"ERRO {tel} ({nome}) -> {detalhe}")
            if detalhe.startswith(("190", "131031", "131048", "131056")):
                print("Parando: problema de token, conta ou limite de envio da Meta.")
                break
        wb.save(args.planilha)          # salva a cada envio: não perde progresso
        time.sleep(args.intervalo)

    if not args.teste:
        wb.save(args.planilha)
    print(f"\nResumo: {enviados} {'simulados' if args.teste else 'enviados'}, {pulados} pulados, {erros} erros.")


if __name__ == "__main__":
    main()
