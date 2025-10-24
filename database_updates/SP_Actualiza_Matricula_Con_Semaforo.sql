USE [SAE]
GO

/****** 
 Stored Procedure: SP_Actualiza_Matricula_Por_Unidad_Academica
 
 MODIFICACIÓN: Ahora acepta parámetro @IdSemaforo para actualizar el estado del semáforo
 
 Autor: Angel Miranda N
 Fecha Creación: 20251008
 Última Modificación: 20251023
 
 Cambios:
 - Agregado parámetro @IdSemaforo (default = 2)
 - El SP ahora actualiza el semáforo al valor especificado
 - Cuando @IdSemaforo = 2: "Se actualiza la matrícula" (guardado parcial)
 - Cuando @IdSemaforo = 3: "Se finaliza y valida la matrícula" (validación completa)
 
******/

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER PROCEDURE [dbo].[SP_Actualiza_Matricula_Por_Unidad_Academica] 
    (
      @UUsuario as nvarchar(50)
    , @PPeriodo as nvarchar(50)
    , @HHost as nvarchar(50)
    , @NNivel as nvarchar(50)
    , @IdSemaforo as int = 2  -- ⭐ NUEVO: Por defecto 2 (parcial), puede ser 3 (completado)
    )
AS

BEGIN TRAN

DECLARE @mensaje as nvarchar(100)

BEGIN TRY

    --**************************************************************
    -- Actualiza la tabla de semaforo_semestre_Unidad_academica
    -- con el estado especificado en @IdSemaforo
    --**************************************************************

    UPDATE [dbo].[Semaforo_Semestre_Unidad_academica]
        SET Id_Semaforo = @IdSemaforo,  -- ⭐ Usa el parámetro recibido
            Fecha_Modificacion = GETDATE()
        FROM [dbo].[Semaforo_Semestre_Unidad_academica] ssau, 
             [dbo].[Temp_Matricula] tmp 
            INNER JOIN [dbo].[Cat_Periodo] per ON tmp.periodo = per.periodo 
            INNER JOIN [dbo].[Cat_Unidad_Academica] UA ON tmp.sigla = UA.sigla 
            INNER JOIN [dbo].[Cat_Programas] pro ON tmp.Nombre_Programa = pro.Nombre_Programa
            INNER JOIN [dbo].[Programa_Modalidad] pm ON pm.id_programa = pro.Id_Programa 
            INNER JOIN [dbo].[Cat_Semestre] sem ON tmp.Semestre = sem.Semestre 
        WHERE ssau.id_Unidad_Academica = ua.id_Unidad_Academica
            AND ssau.id_semestre = sem.id_semestre
            AND ssau.Id_Periodo = per.Id_Periodo
            AND ssau.Id_Unidad_Academica = ua.Id_Unidad_Academica
            AND ssau.Id_Modalidad_Programa = pm.Id_Modalidad_Programa;

    --**************************************************************
    -- Actualiza la tabla de Matrícula por Unidad Académica
    --**************************************************************

    UPDATE [dbo].[Matricula] 
        SET Matricula = tmp.Matricula
        FROM [dbo].[matricula] mat, [dbo].[Temp_Matricula] tmp 
            INNER JOIN [dbo].[Cat_Periodo] per ON tmp.periodo = per.periodo
            INNER JOIN [dbo].[Cat_Unidad_Academica] UA ON tmp.sigla = UA.sigla
            INNER JOIN [dbo].[Cat_Programas] pro ON tmp.Nombre_Programa = pro.Nombre_Programa
            INNER JOIN [dbo].[Cat_Rama] ram ON tmp.Nombre_Rama = ram.Nombre_Rama
            INNER JOIN [dbo].[Cat_Nivel] niv ON tmp.Nivel = niv.Nivel
            INNER JOIN [dbo].[Cat_Semestre] sem ON tmp.Semestre = sem.Semestre
            INNER JOIN [dbo].[Cat_Modalidad] md ON tmp.Modalidad = md.Modalidad
            INNER JOIN [dbo].[Cat_Turno] tur ON tmp.turno = tur.turno
            INNER JOIN [dbo].[Cat_Grupo_Edad] ge ON tmp.Grupo_Edad = ge.Grupo_Edad
            INNER JOIN [dbo].[Cat_Sexo] sex ON tmp.sexo = sex.Sexo
            INNER JOIN [dbo].[Cat_Tipo_Ingreso] tip ON tmp.Tipo_Ingreso = tip.Tipo_de_Ingreso
        WHERE mat.Id_periodo = per.id_periodo
            AND mat.Id_Unidad_Academica = ua.Id_Unidad_Academica
            AND mat.Id_Programa = pro.Id_Programa
            AND mat.Id_Rama = ram.Id_Rama
            AND mat.Id_Nivel = niv.Id_Nivel
            AND mat.Id_Modalidad = md.Id_Modalidad	
            AND mat.Id_Turno = tur.Id_Turno
            AND mat.Id_Semestre = sem.id_Semestre
            AND mat.Id_Grupo_Edad = ge.Id_Grupo_Edad
            AND mat.id_Tipo_Ingreso = tip.Id_Tipo_Ingreso
            AND mat.Id_Sexo = sex.Id_Sexo;

    -- Limpiar tabla temporal
    TRUNCATE TABLE Temp_Matricula;

    -- Mensaje dinámico según el estado del semáforo
    SET @mensaje = CASE 
        WHEN @IdSemaforo = 3 THEN 'Se finaliza y valida la matrícula'
        WHEN @IdSemaforo = 2 THEN 'Se actualiza la matrícula con datos parciales'
        ELSE 'Se actualiza la matrícula'
    END;

    -- Registrar en bitácora
    EXEC [dbo].[SP_Registra_Bitacora] 
        @Usuario = @UUsuario,
        @Modulo = 'Mod_Matricula',
        @Periodo = @PPeriodo,
        @Accion = @mensaje,
        @Host = @HHost;

    COMMIT TRAN

END TRY

BEGIN CATCH

    ROLLBACK TRAN

    SET @mensaje = 'Falla la Actualización de la matrícula: ' + ERROR_MESSAGE();

    EXEC [dbo].[SP_Registra_Bitacora] 
        @Usuario = @UUsuario,
        @Modulo = 'Mod_Matricula',
        @Periodo = @PPeriodo,
        @Accion = @mensaje,
        @Host = @HHost;

END CATCH;

GO

/*
EJEMPLOS DE USO:

-- Guardado parcial (semáforo = 2, amarillo)
EXEC [dbo].[SP_Actualiza_Matricula_Por_Unidad_Academica] 
    @UUsuario = 'juan.perez',
    @PPeriodo = '2025-2026/1',
    @HHost = 'LAPTOP-123',
    @NNivel = 'Superior';
    -- @IdSemaforo se omite, usa default = 2

-- Validación completa (semáforo = 3, verde)
EXEC [dbo].[SP_Actualiza_Matricula_Por_Unidad_Academica] 
    @UUsuario = 'juan.perez',
    @PPeriodo = '2025-2026/1',
    @HHost = 'LAPTOP-123',
    @NNivel = 'Superior',
    @IdSemaforo = 3;  -- Marca como completado

*/
