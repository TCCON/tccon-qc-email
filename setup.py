from setuptools import setup

if __name__ == '__main__':
    setup(
            name='tccon_qc_email',
            description='Email QA/QC plots of TCCON data to GGGBugs',
            author='Sebastien Roche & Joshua Laughner',
            author_email='sebastien.roche@mail.utoronto.ca; jlaugh@caltech.edu',
            version='1.0.0',
            url='https://github.com/WennbergLab/tccon-qc-email',
            install_requires=[
                    'tomli>=1.0.4'
                ],
            packages=['qc_email'],
            python_requires='>=3.7'
    )
