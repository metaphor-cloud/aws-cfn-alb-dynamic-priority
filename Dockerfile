FROM public.ecr.aws/lambda/python:3.13 AS base
WORKDIR /app

FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
RUN python -m pytest

FROM base AS app
COPY src .
# RUN pip install -r requirements.txt
CMD ["index.handler"]
