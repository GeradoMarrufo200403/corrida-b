from contextlib import contextmanager

from fastapi import Request


@contextmanager
def unit_of_work(request: Request):
    """Una transacción por petición: commit si todo sale bien, rollback ante cualquier error.
    Los routers usan siempre este bloque para llegar a los servicios."""
    container = request.app.state.container
    with container.session_factory() as session:
        try:
            yield container.build(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
