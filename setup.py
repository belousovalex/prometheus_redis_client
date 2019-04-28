from distutils.core import setup

setup(
    name='prometheus_redis_client',
    packages=['prometheus_redis_client'],
    version='0.2.0',
    description='Python prometheus multiprocessing client which used redis as metric storage.',
    author='Belousov Alex',
    author_email='belousov.aka.alfa@gmail.com',
    url='https://github.com/belousovalex/prometheus_redis_client',
    install_requires=['redis>=3.2.1,<4.0.0', ],
    license='Apache 2',
)
