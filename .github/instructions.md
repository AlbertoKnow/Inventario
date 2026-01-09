# Instrucciones Generales del Proyecto

Este documento define las **buenas prácticas y lineamientos generales** que deben seguirse al contribuir y desarrollar dentro de este repositorio. El objetivo es mantener un código **limpio, mantenible, seguro y escalable**.

---

## 1. Buenas prácticas de desarrollo

* Escribe código **claro y legible** antes que código complejo.
* Sigue los principios **KISS**, **DRY** y **YAGNI**.
* Evita duplicar lógica: reutiliza funciones, módulos o componentes.
* Mantén las funciones y clases con **una sola responsabilidad** (SRP).
* Usa nombres descriptivos para variables, funciones, clases y archivos.
* Evita comentarios innecesarios: el código debe explicarse por sí mismo.

---

## 2. Estructura y organización del código

* Mantén una estructura de carpetas coherente y predecible.
* Separa responsabilidades (por ejemplo: lógica de negocio, acceso a datos, presentación).
* No mezcles código experimental con código estable.
* Elimina archivos, funciones o dependencias que ya no se utilicen.

---

## 3. Documentación

* Documenta el código cuando sea necesario, especialmente:

  * Funciones o métodos complejos
  * Algoritmos no triviales
  * Decisiones técnicas importantes
* Usa comentarios y/o herramientas de documentación estándar del lenguaje (ej: JSDoc, docstrings, etc.).
* Mantén actualizado el `README.md` si se agregan cambios relevantes al proyecto.
* Documenta cualquier configuración especial o pasos adicionales necesarios para ejecutar el proyecto.

---

## 4. Pruebas de software

* Escribe **pruebas unitarias** para la lógica crítica del sistema.
* Agrega **pruebas de integración** cuando sea necesario.
* Asegúrate de que las pruebas sean:

  * Repetibles
  * Claras
  * Independientes entre sí
* No envíes cambios que rompan pruebas existentes.
* Siempre que sea posible, escribe las pruebas junto con el desarrollo de la funcionalidad.

---

## 5. Refactorización

* Refactoriza el código cuando:

  * Se detecte duplicación
  * La complejidad aumente innecesariamente
  * La legibilidad se vea afectada
* La refactorización **no debe cambiar el comportamiento del sistema**.
* Asegúrate de que las pruebas sigan pasando después de refactorizar.

---

## 6. Control de versiones (Git)

* Realiza commits pequeños y significativos.
* Usa mensajes de commit claros y descriptivos.
* Evita subir:

  * Archivos generados automáticamente
  * Credenciales, tokens o información sensible
* Revisa los cambios antes de hacer un commit o pull request.

---

## 7. Seguridad

* No incluyas secretos en el código fuente.
* Usa variables de entorno para configuraciones sensibles.
* Valida entradas del usuario y maneja errores adecuadamente.
* Mantén dependencias actualizadas cuando sea posible.

---

## 8. Calidad y mejora continua

* Prioriza la calidad sobre la rapidez.
* Revisa tu propio código antes de enviarlo.
* Acepta sugerencias y feedback de otros colaboradores.
* Busca constantemente oportunidades de mejora en el código y en los procesos.

---

## 9. Stack tecnológico y herramientas

Este proyecto define explícitamente el **stack tecnológico** a utilizar. Este punto debe ajustarse según el proyecto, manteniendo el resto de este documento sin cambios.

### Tecnologías principales

* Lenguaje(s): Python 3.8+
* Framework(s): Django 4.2.8
* Frontend: Django Templates + Bootstrap 5
* Entorno de ejecución: Python Virtual Environment (venv)

### Dependencias y librerías

* Gestor de dependencias: pip
* Librerías principales:
  - Django 4.2.8 - Framework web Python
  - python-decouple 3.8 - Gestión de variables de entorno
  - Pillow (opcional) - Procesamiento de imágenes

### Base de datos

* Tipo (relacional / no relacional): Relacional
* Motor: SQLite (desarrollo), PostgreSQL o MySQL (producción recomendado)

### Herramientas de desarrollo

* Control de versiones: Git
* Formateo y linting: PEP 8 compliance
* Testing: Django TestCase (unittest)
* Virtual Environment: Python venv
* Entorno de desarrollo recomendado: Visual Studio Code

> **Nota:** Antes de introducir una nueva tecnología, evalúa su necesidad, impacto y mantenimiento a largo plazo.

---

## 10. Consideraciones finales

El cumplimiento de estas instrucciones ayuda a mantener un proyecto más profesional, confiable y fácil de mantener a largo plazo. Todos los aportes deben alinearse con estos principios.

---

**Gracias por contribuir y mantener la calidad del proyecto.**
