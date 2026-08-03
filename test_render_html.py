"""Testes da conversao de marcacoes para HTML do Telegram.

Rode com:  python test_render_html.py
"""
from telegram_api import render_html

CASOS = [
    # ---------------------------------------------------------------- links ---
    ("link simples",
     "[clique aqui](https://site.com)",
     '<a href="https://site.com">clique aqui</a>'),

    # A URL nao pode ser tocada pelas marcacoes de negrito/italico.
    ("url com underline nao vira italico",
     "[clique aqui](https://site.com/promo_black_friday)",
     '<a href="https://site.com/promo_black_friday">clique aqui</a>'),

    ("url com asterisco nao vira negrito",
     "[clique aqui](https://site.com/a*b*c)",
     '<a href="https://site.com/a*b*c">clique aqui</a>'),

    # O & da querystring so pode ser escapado uma vez.
    ("url com & escapa uma vez so",
     "[clique aqui](https://site.com/x?a=1&b=2)",
     '<a href="https://site.com/x?a=1&amp;b=2">clique aqui</a>'),

    # Link escrito sem http:// (caso mais comum de quem nao e tecnico).
    ("url sem esquema ganha https",
     "[clique aqui](www.site.com)",
     '<a href="https://www.site.com">clique aqui</a>'),

    ("dominio sem www e sem esquema",
     "[clique aqui](site.com.br/promo)",
     '<a href="https://site.com.br/promo">clique aqui</a>'),

    # Espaco entre ] e ( nao pode quebrar o link.
    ("espaco antes do parentese",
     "[clique aqui] (https://site.com)",
     '<a href="https://site.com">clique aqui</a>'),

    ("parenteses dentro da url",
     "[clique aqui](https://pt.wikipedia.org/wiki/Bot_(informatica))",
     '<a href="https://pt.wikipedia.org/wiki/Bot_(informatica)">clique aqui</a>'),

    ("link do telegram",
     "[entrar](tg://resolve?domain=canal)",
     '<a href="tg://resolve?domain=canal">entrar</a>'),

    ("dois links na mesma linha",
     "[um](https://a.com/x_y) e [dois](https://b.com/z_w)",
     '<a href="https://a.com/x_y">um</a> e <a href="https://b.com/z_w">dois</a>'),

    ("negrito dentro do rotulo do link",
     "[*clique aqui*](https://site.com)",
     '<a href="https://site.com"><b>clique aqui</b></a>'),

    # ------------------------------------------------- negrito e italico -----
    ("negrito", "*oi*", "<b>oi</b>"),
    ("italico", "_oi_", "<i>oi</i>"),
    ("negrito fora do link continua funcionando",
     "*Promo!* [clique aqui](https://site.com/promo_1)",
     '<b>Promo!</b> <a href="https://site.com/promo_1">clique aqui</a>'),

    # ------------------------------------------------------------ escaping ---
    ("caracteres html do usuario sao escapados",
     "5 < 10 & 20 > 3",
     "5 &lt; 10 &amp; 20 &gt; 3"),

    # Aspas no rotulo sao conteudo de texto, nao atributo: nao precisam escapar.
    ("aspas no rotulo nao quebram o href",
     '[a"b](https://site.com)',
     '<a href="https://site.com">a"b</a>'),

    ("aspas na url sao escapadas",
     '[x](https://site.com/a"b)',
     '<a href="https://site.com/a&quot;b">x</a>'),

    # -------------------------------------------------------------- bordas ---
    ("texto vazio", "", ""),
    ("colchete sem link fica literal",
     "[so um colchete] e mais texto",
     "[so um colchete] e mais texto"),
]


def main():
    falhas = 0
    for nome, entrada, esperado in CASOS:
        obtido = render_html(entrada)
        if obtido == esperado:
            print(f"  ok   {nome}")
        else:
            falhas += 1
            print(f"  FALHA {nome}")
            print(f"        entrada  : {entrada!r}")
            print(f"        esperado : {esperado!r}")
            print(f"        obtido   : {obtido!r}")
    print(f"\n{len(CASOS) - falhas}/{len(CASOS)} passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
