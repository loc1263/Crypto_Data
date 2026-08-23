"""
Presencia de este archivo en la raíz del proyecto hace que pytest inserte
esta carpeta en sys.path (modo de import "prepend", el default), para que
`import core...` funcione en los tests sin importar desde qué directorio
se invoque `pytest`.
"""
