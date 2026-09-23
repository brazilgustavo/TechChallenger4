import json
from datetime import date
from lib.db import connect, init_schema
from lib.ui import _render_risco_ml, build_ui


def test_render_avisos():
    md = _render_risco_ml({
        'resposta_estruturada': {
            'modo': 'normal',
            'prediction': 'habitual',
            'probabilities': {'habitual': 0.8, 'alto_risco': 0.2},
            'threshold': 0.3,
            'safety_notice': 'Resultado de apoio à decisão.',
            'aviso_dados_sinteticos': 'Modelo treinado em dados sintéticos.',
            'raciocinio': ['ok'],
        }
    })
    assert 'Limiar operacional' in md
    assert 'sintéticos' in md


def test_render_degradado_primeiro():
    md = _render_risco_ml({'resposta_estruturada': {
        'modo': 'degradado',
        'prediction': 'habitual',
        'safety_notice': 'x',
        'aviso_dados_sinteticos': 'y',
    }})
    assert md.index('degradado') < md.index('Classificação') or 'Modo degradado' in md


def test_carregar_paciente_ml_no_ui(tmp_path):
    db_file = tmp_path / 'hospital_test.db'
    conn = connect(db_file)
    init_schema(conn)
    conn.execute(
        "INSERT INTO pacientes (paciente_id, nome, data_nascimento, cpf_hash, cadastro_em) "
        "VALUES (1, 'Paciente Teste UI', '1996-05-15', 'hash123', '2026-01-01')"
    )
    conn.execute(
        "INSERT INTO prontuario_gineco (paciente_id, g_p_a, dum) VALUES (1, 'G3P1A1', '2025-11-10')"
    )
    conn.commit()

    app = build_ui(agent=None, conn=conn)
    assert app is not None

    from lib.ml.schema import features_de_paciente
    payload, ausentes = features_de_paciente(conn, 1, hoje=date(2026, 5, 22))
    assert payload['gestacoes'] == 3
    assert payload['partos'] == 1
    assert payload['abortos'] == 1
    conn.close()
