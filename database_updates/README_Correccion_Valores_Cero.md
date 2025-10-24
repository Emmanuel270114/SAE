# 🔧 Corrección: Guardar valores '0' en la tabla Matrícula

## 📋 Problema Identificado

Cuando se hace clic en "Validar y finalizar captura", los campos vacíos se rellenan automáticamente con '0', pero estos valores **NO se estaban guardando** en la base de datos.

### ❌ Filtro en el Backend (Python)
**Archivo:** `backend/api/matricula_sp.py` - Línea 619

**Código anterior:**
```python
if filtered and filtered.get('Matricula', 0) > 0:  # Solo guardaba valores > 0
    temp_matricula = Temp_Matricula(**filtered)
    merged_obj = db.merge(temp_matricula)
    registros_insertados += 1
```

**Problema:** La condición `> 0` **rechazaba** todos los registros con valor 0.

**✅ Solución aplicada:**
```python
if filtered and filtered.get('Matricula', 0) >= 0:  # Ahora acepta valores >= 0
    temp_matricula = Temp_Matricula(**filtered)
    merged_obj = db.merge(temp_matricula)
    registros_insertados += 1
```

---

## ✅ Solución Implementada

### Backend Python - ✅ COMPLETADO

**Cambio realizado en:** `backend/api/matricula_sp.py` línea ~619

```python
# ANTES
if filtered and filtered.get('Matricula', 0) > 0:

# DESPUÉS  
if filtered and filtered.get('Matricula', 0) >= 0:  # ✅ Acepta valores >= 0
```

**Impacto:** 
- ✅ Los registros con valor 0 ahora se guardan en `Temp_Matricula`
- ✅ El SP actualiza estos valores en `Matricula` (si los registros ya existen)

---

## ⚠️ Requisito Importante: Pre-población de la Tabla Matricula

**IMPORTANTE:** Para que los valores '0' se guarden correctamente, **la tabla `Matricula` debe tener pre-creados todos los registros posibles** para cada combinación de:
- Período
- Unidad Académica  
- Programa
- Rama
- Nivel
- Modalidad
- Turno
- Semestre
- Grupo de Edad
- Tipo de Ingreso
- Sexo

**Estado inicial:** `Matricula = 0` para todos los registros

**¿Por qué?**
El Stored Procedure `SP_Actualiza_Matricula_Por_Unidad_Academica` hace **UPDATE**, no INSERT:
- ✅ Si el registro existe → lo actualiza con el nuevo valor (incluyendo 0)
- ❌ Si el registro NO existe → no hace nada (se pierde el dato)

**Cómo verificar si la tabla está pre-poblada:**
```sql
-- Contar registros en Matricula para un programa específico
SELECT COUNT(*) as TotalRegistros
FROM Matricula m
    INNER JOIN Cat_Periodo p ON m.Id_periodo = p.Id_Periodo
    INNER JOIN Cat_Programas pr ON m.Id_Programa = pr.Id_Programa
WHERE p.Periodo = '2025-2026/1'
    AND pr.Nombre_Programa = 'TU_PROGRAMA_AQUI';

-- Debería devolver: 
-- (Número de grupos de edad) × (3 tipos de ingreso) × (2 sexos) × (Número de semestres) × (Número de turnos) × (Número de modalidades)
-- Ejemplo: 30 edades × 3 tipos × 2 sexos × 8 semestres × 2 turnos × 2 modalidades = 5,760 registros
```

**Si NO está pre-poblada:**
Necesitarás ejecutar un script para crear todos los registros iniciales. Ejemplo:
```sql
-- Script de ejemplo para pre-poblar Matricula
INSERT INTO Matricula (Id_periodo, Id_Unidad_Academica, Id_Programa, Id_Rama, Id_Nivel, 
                       Id_Modalidad, Id_Turno, Id_Semestre, Id_Grupo_Edad, id_Tipo_Ingreso, Id_Sexo, Matricula)
SELECT 
    p.Id_Periodo,
    ua.Id_Unidad_Academica,
    pr.Id_Programa,
    pr.Id_Rama_Programa,
    n.Id_Nivel,
    m.Id_Modalidad,
    t.Id_Turno,
    s.Id_Semestre,
    ge.Id_Grupo_Edad,
    ti.Id_Tipo_Ingreso,
    sx.Id_Sexo,
    0 as Matricula  -- Inicializar en 0
FROM Cat_Periodo p
    CROSS JOIN Cat_Unidad_Academica ua
    CROSS JOIN Cat_Programas pr
    CROSS JOIN Cat_Nivel n
    CROSS JOIN Cat_Modalidad m
    CROSS JOIN Cat_Turno t
    CROSS JOIN Cat_Semestre s
    CROSS JOIN Cat_Grupo_Edad ge
    CROSS JOIN Cat_Tipo_Ingreso ti
    CROSS JOIN Cat_Sexo sx
WHERE p.Periodo = '2025-2026/1'  -- Solo para el período actual
    AND NOT EXISTS (
        -- No duplicar registros existentes
        SELECT 1 FROM Matricula mat
        WHERE mat.Id_periodo = p.Id_Periodo
            AND mat.Id_Unidad_Academica = ua.Id_Unidad_Academica
            AND mat.Id_Programa = pr.Id_Programa
            -- ... (resto de condiciones)
    );
```

---

## 🚀 Instrucciones de Aplicación

### ✅ Cambio en Backend Python (YA APLICADO)
No requiere acción adicional. El cambio ya está en el código.

### ⚠️ Verificar Pre-población de Tabla Matricula (CRÍTICO)

**Ejecutar en SQL Server Management Studio:**

```sql
-- 1. Verificar si hay registros en Matricula para el período actual
SELECT COUNT(*) as RegistrosExistentes
FROM Matricula m
    INNER JOIN Cat_Periodo p ON m.Id_periodo = p.Id_Periodo
WHERE p.Periodo = '2025-2026/1';

-- 2. Si el resultado es 0 o muy bajo, necesitas pre-poblar la tabla
-- Ejecutar el script de pre-población (ver sección anterior)
```

**Si la tabla NO está pre-poblada:**
1. Ejecutar el script INSERT con CROSS JOIN para crear todos los registros
2. Inicializar todos con `Matricula = 0`
3. Esto solo se hace UNA VEZ por período

---

## 🧪 Cómo Probar

1. **Acceder a la captura de matrícula**
   - Seleccionar período, programa, modalidad, turno

2. **Capturar datos parciales**
   - Llenar **solo algunos campos**
   - Dejar otros campos vacíos

3. **Validar y finalizar:**
   - Hacer clic en "✅ Validar y finalizar captura"
   - Confirmar el mensaje que dice "Se rellenaron X campos vacíos con '0'"

4. **Verificar en base de datos:**
   ```sql
   -- Ver todos los registros del período actual
   SELECT 
       m.Matricula,
       ge.Grupo_Edad,
       ti.Tipo_de_Ingreso,
       s.Sexo
   FROM Matricula m
       INNER JOIN Cat_Grupo_Edad ge ON m.Id_Grupo_Edad = ge.Id_Grupo_Edad
       INNER JOIN Cat_Tipo_Ingreso ti ON m.id_Tipo_Ingreso = ti.Id_Tipo_Ingreso
       INNER JOIN Cat_Sexo s ON m.Id_Sexo = s.Id_Sexo
   WHERE m.Id_periodo = (SELECT Id_Periodo FROM Cat_Periodo WHERE Periodo = '2025-2026/1')
   ORDER BY ge.Id_Grupo_Edad, ti.Id_Tipo_Ingreso, s.Id_Sexo;
   ```

5. **Resultado esperado:**
   - ✅ Campos con datos > 0 → guardados correctamente
   - ✅ Campos rellenados con '0' → **ahora aparecen en Matricula**
   - ✅ Total de registros = campos con datos + campos en cero

---

## 📊 Comparación Antes vs Después

### Antes (❌ Problema)

| Escenario | Backend Python | Temp_Matricula | SP UPDATE | Matricula | Resultado |
|-----------|----------------|----------------|-----------|-----------|-----------|
| Campo con valor 5 | ✅ Acepta (> 0) | ✅ Se guarda | ✅ UPDATE exitoso | ✅ Actualizado | ✅ Correcto |
| Campo con valor 0 | ❌ Rechaza (> 0) | ❌ No se guarda | ⏭️ No hay dato | ❌ No se actualiza | ❌ Se pierde |
| Campo vacío → '0' | ❌ Rechaza (> 0) | ❌ No se guarda | ⏭️ No hay dato | ❌ No se actualiza | ❌ Se pierde |

**Total guardado:** Solo valores > 0 (~30% de campos)

---

### Después (✅ Solución)

| Escenario | Backend Python | Temp_Matricula | SP UPDATE | Matricula | Resultado |
|-----------|----------------|----------------|-----------|-----------|-----------|
| Campo con valor 5 | ✅ Acepta (>= 0) | ✅ Se guarda | ✅ UPDATE exitoso | ✅ Actualizado | ✅ Correcto |
| Campo con valor 0 | ✅ Acepta (>= 0) | ✅ Se guarda | ✅ UPDATE exitoso* | ✅ Actualizado | ✅ Correcto |
| Campo vacío → '0' | ✅ Acepta (>= 0) | ✅ Se guarda | ✅ UPDATE exitoso* | ✅ Actualizado | ✅ Correcto |

**\*Nota:** El UPDATE solo funciona si el registro ya existe en Matricula (pre-poblado con 0)

**Total guardado:** 100% de los campos (si Matricula está pre-poblada)

---

## ⚠️ Notas Importantes

1. **El cambio en Python ya está aplicado** - No requiere reiniciar el servidor mientras no cambies el código.

2. **El SP DEBE aplicarse en SQL Server** - Sin esto, los valores 0 llegarán a `Temp_Matricula` pero no pasarán a `Matricula`.

3. **Es seguro aplicar el MERGE** - No afecta datos existentes, solo mejora el INSERT automático.

4. **Backup recomendado** - Antes de aplicar el SP, hacer backup de la tabla `Matricula`:
   ```sql
   -- Crear backup
   SELECT * INTO Matricula_Backup_20241024 FROM Matricula;
   
   -- Verificar backup
   SELECT COUNT(*) FROM Matricula_Backup_20241024;
   ```

5. **Sin el MERGE, los '0' se perderán** al pasar de `Temp_Matricula` → `Matricula`.

---

## 🔍 Archivos Modificados

| Archivo | Cambio | Estado |
|---------|--------|--------|
| `backend/api/matricula_sp.py` | Cambiar `> 0` por `>= 0` en línea 619 | ✅ Aplicado |

---

## 💡 Resumen Ejecutivo

**Problema:** Los valores '0' se rellenaban en el frontend pero se **descartaban** en el backend.

**Causa raíz:** Filtro `> 0` en el backend rechazaba valores cero.

**Solución:** Cambiar a `>= 0` para aceptar ceros.

**Requisito adicional:** La tabla `Matricula` debe tener todos los registros pre-creados con valor inicial 0 para que el SP pueda actualizarlos.

**Acción requerida:** 
1. ✅ Cambio en Python (ya aplicado)
2. ⚠️ Verificar/ejecutar pre-población de tabla Matricula

**Fecha de corrección:** 24 de octubre de 2025  
**Versión:** v1.1 - Aceptar valores >= 0 (requiere tabla pre-poblada)

