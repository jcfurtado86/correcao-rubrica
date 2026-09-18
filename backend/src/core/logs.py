"""Filtro de log que impede texto de estudante de chegar aos logs (Princípio IV).

Os logs são o lugar mais fácil de vazar dado: um `logger.info(resposta)` num
ponto qualquer e o texto vai parar num arquivo sem controle de acesso. O filtro
remove os atributos conhecidos por carregar texto e trunca a mensagem, para que
nem um descuido grave o conteúdo inteiro.
"""

import logging

CAMPOS_PROIBIDOS = ("texto", "resposta_bruta", "justificativa", "trechos")
LIMITE_MENSAGEM = 500


class FiltroSemTexto(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for campo in CAMPOS_PROIBIDOS:
            if hasattr(record, campo):
                setattr(record, campo, "[removido]")
        mensagem = record.getMessage()
        if len(mensagem) > LIMITE_MENSAGEM:
            record.msg = mensagem[:LIMITE_MENSAGEM] + " [truncado]"
            record.args = ()
        return True
