FROM public.ecr.aws/lambda/python:3.10.2023.07.13.16
COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY ./PSA ${LAMBDA_TASK_ROOT}/PSA
COPY ./DesalinationModels ${LAMBDA_TASK_ROOT}/DesalinationModels
COPY ./SAM_flatJSON ${LAMBDA_TASK_ROOT}/SAM_flatJSON
COPY ./supported_params.py ${LAMBDA_TASK_ROOT}
COPY ["USA AZ Scottsdale Muni (TMY3).csv", "${LAMBDA_TASK_ROOT}"]
COPY ./model_selection_test.json ${LAMBDA_TASK_ROOT}
# COPY ./coinhsl-2023.05.26.tar.gz ${LAMBDA_TASK_ROOT}
# COPY ./metis-5.1.0.tar.gz ${LAMBDA_TASK_ROOT}
RUN yum install -y lapack-devel blas-devel
RUN yum install -y compat-gcc-48-libgfortran.x86_64
RUN pip install -r requirements.txt
RUN idaes get-extensions --distro centos7 --to /var/task
CMD [ "lambda_function.handler" ]
