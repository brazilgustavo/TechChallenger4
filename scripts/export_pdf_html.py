from pathlib import Path
import markdown_it

root = Path(__file__).resolve().parents[1]
md_path = root / 'RELATORIO_TECNICO.md'
html_path = root / 'RELATORIO_TECNICO.html'

md_text = md_path.read_text(encoding='utf-8')
md_parser = markdown_it.MarkdownIt()
html_body = md_parser.render(md_text)

html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Relatório Técnico — Guardiã AI (Saúde e Segurança da Mulher)</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 40px auto;
            max-width: 900px;
            line-height: 1.6;
            color: #1e293b;
            background: #ffffff;
            padding: 0 20px;
        }}
        h1, h2, h3, h4 {{
            color: #0f172a;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 24px;
        }}
        code {{
            background: #f1f5f9;
            color: #0f172a;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: Consolas, Monaco, monospace;
            font-size: 0.9em;
        }}
        pre code {{
            display: block;
            padding: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            padding: 10px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8fafc;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        blockquote {{
            border-left: 4px solid #2563eb;
            margin: 16px 0;
            padding: 8px 16px;
            background-color: #eff6ff;
            color: #1e40af;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 0;
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""

html_path.write_text(html_template, encoding='utf-8')
print(f"RELATORIO_TECNICO.html gerado com sucesso em {html_path}")
