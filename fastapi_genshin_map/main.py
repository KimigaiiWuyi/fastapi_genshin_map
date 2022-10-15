import logging

from fastapi import FastAPI
from GetMapImage import get_map_image

gsm = FastAPI(title='GsMAP', description='GenshinMap API')
gsm.include_router(get_map_image.router, prefix='/map')


@gsm.get("/")
def read_root():
    return {'message': '这是一个原神地图API'}


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find('/') == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app=gsm, host='0.0.0.0', port=5000)
