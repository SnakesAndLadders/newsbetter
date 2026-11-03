from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename, 'r') as f:
        return f.read().splitlines()


# Use README for long description
with open('README.md', 'r') as readme_fp:
    long_description = readme_fp.read()

setup(
    name="NewsBetter",
    version="1.5.0",
    author="Shawn Ayotte",
    author_email="shawn.k.ayotte@gmail.com",
    description="Yet another RSS news reader ",
    license="MIT",
    keywords="",
    url="https://github.com/SnakesAndLadders/NewsBetter",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages = find_packages(exclude=['tests', 'docs']),
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'NewsBetter = NewsBetter:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',

        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

)
