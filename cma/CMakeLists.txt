install(PROGRAMS AssimCclasses.py AssimCtypes.py cma.py frameinfo.py __init__.py
        COMPONENT cma DESTINATION ${PYINSTALL})
install(DIRECTORY tests
        COMPONENT cma DESTINATION ${PYINSTALL} PATTERN "*.txt" EXCLUDE PATTERN "*.pyc" EXCLUDE)
