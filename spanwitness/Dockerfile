FROM public.ecr.aws/lambda/python:3.14@sha256:fc4e15a5e09e2c9b6184810ea0fdc87afe1c1c734c98cbe27d739a35c3f15e7e
COPY spanwitness/requirements.txt spanwitness/requirements-aws.txt spanwitness/requirements-lock.txt ${LAMBDA_TASK_ROOT}/spanwitness/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/spanwitness/requirements-aws.txt -c ${LAMBDA_TASK_ROOT}/spanwitness/requirements-lock.txt
COPY spanwitness ${LAMBDA_TASK_ROOT}/spanwitness
ENV SPANWITNESS_DATA=/tmp/spanwitness
CMD ["spanwitness.lambda_handler.handler"]
