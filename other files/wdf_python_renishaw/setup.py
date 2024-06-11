import setuptools
import wdf

setuptools.setup(
    name=wdf.__title__,
    version=wdf.__version__,
    description=wdf.__doc__.split("\n")[0],
    long_description="\n".join(wdf.__doc__.split("\n")[2:]).strip(),
    author=wdf.__author__,
    author_email=wdf.__author_email__,
    license=wdf.__license__,
    packages=['wdf'],
    platforms=['any'],
    install_requires=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Physics',
    ],
)
