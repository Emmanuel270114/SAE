# Instrucciones para trabajar con el repositorio SAE-Nuevo

## Subir el proyecto a un nuevo repositorio

1. **Crear un nuevo repositorio en GitHub**
   - Ve a [GitHub](https://github.com) y accede a tu cuenta.
   - Haz clic en el botón **New** (Nuevo) en la parte superior derecha.
   - Ingresa un nombre para tu repositorio (por ejemplo, `SAE-Nuevo`).
   - Configura la visibilidad (público o privado) y haz clic en **Create repository**.

2. **Actualizar el repositorio local para apuntar al nuevo repositorio**
   - Abre tu terminal y navega al directorio del proyecto.
   - Ejecuta los siguientes comandos:

     ```bash
     git remote remove origin
     git remote add origin https://github.com/tu-usuario/SAE-Nuevo.git
     ```

     Reemplaza `tu-usuario` con tu nombre de usuario de GitHub y `SAE-Nuevo` con el nombre del nuevo repositorio.

3. **Subir los cambios al nuevo repositorio**
   - Sube todos los cambios al nuevo repositorio:

     ```bash
     git push -u origin main
     ```

4. **Verificar que los cambios se hayan subido correctamente**
   - Ve al nuevo repositorio en GitHub y verifica que los archivos estén presentes.

---

## Actualizar el repositorio con nuevos cambios

1. **Verificar el estado del repositorio local**
   - Antes de realizar cambios, verifica el estado de tu repositorio:

     ```bash
     git status
     ```

2. **Agregar los cambios realizados**
   - Agrega los archivos modificados al área de preparación:

     ```bash
     git add .
     ```

3. **Crear un commit con un mensaje descriptivo**
   - Crea un commit para guardar los cambios localmente:

     ```bash
     git commit -m "Descripción de los cambios realizados"
     ```

4. **Subir los cambios al repositorio remoto**
   - Sube los cambios al repositorio remoto:

     ```bash
     git push origin main
     ```

5. **Actualizar el repositorio local si hay cambios remotos**
   - Si el repositorio remoto tiene cambios que no están en tu repositorio local, sincroniza los cambios antes de subir los tuyos:

     ```bash
     git pull origin main --rebase
     ```

   - Resuelve cualquier conflicto si es necesario y continúa el proceso de rebase:

     ```bash
     git rebase --continue
     ```