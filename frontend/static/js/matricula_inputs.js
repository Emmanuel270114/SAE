// Configuración global para los inputs de matrícula
const MATRICULA_CONFIG = {
    inputStyles: {
        // El contenedor principal de la celda (para los dos sexos)
        container: 'display:inline-flex;flex-direction:row;gap:6px;justify-content:center;align-items:center;width:auto;',
        // Cajas de cada sexo
        boxMale: 'display:inline-flex;align-items:center;gap:3px;padding:2px 4px;background:#e3f2fd;border-radius:4px;border:1px solid #90caf9;line-height:1;',
        boxFemale: 'display:inline-flex;align-items:center;gap:3px;padding:2px 4px;background:#fce4ec;border-radius:4px;border:1px solid #f48fb1;line-height:1;',
        // Etiquetas
        labelMale: 'font-weight:700;color:#1976d2;font-size:11px;min-width:14px;text-align:center;',
        labelFemale: 'font-weight:700;color:#c2185b;font-size:11px;min-width:14px;text-align:center;',
        // Inputs
        inputMale: 'width:42px;padding:2px 3px;border:2px solid #2196f3;border-radius:3px;background:#fff;color:#1976d2;font-weight:600;text-align:center;font-size:11px;line-height:1.1;',
        inputFemale: 'width:42px;padding:2px 3px;border:2px solid #e91e63;border-radius:3px;background:#fff;color:#c2185b;font-weight:600;text-align:center;font-size:11px;line-height:1.1;'
    },
    labels: {
        male: 'H',  // Hombre
        female: 'M'  // Mujer
    }
};

// Función para crear un input de matrícula
function crearInputMatricula(tipoId, grupoId, sexo, valor = '') {
    const isMale = sexo === 'M';
    const label = isMale ? MATRICULA_CONFIG.labels.male : MATRICULA_CONFIG.labels.female;
    const boxStyle = isMale ? MATRICULA_CONFIG.inputStyles.boxMale : MATRICULA_CONFIG.inputStyles.boxFemale;
    const labelStyle = isMale ? MATRICULA_CONFIG.inputStyles.labelMale : MATRICULA_CONFIG.inputStyles.labelFemale;
    const inputStyle = isMale ? MATRICULA_CONFIG.inputStyles.inputMale : MATRICULA_CONFIG.inputStyles.inputFemale;
    return `<div class="matricula-box ${isMale ? 'matricula-hombre' : 'matricula-mujer'}" style="${boxStyle}"><span class="matricula-label" style="${labelStyle}">${label}</span><input type="number" id="input_${tipoId}_${grupoId}_${sexo}" value="${valor}" min="0" class="input-matricula-nueva" data-tipo-ingreso="${tipoId}" data-grupo-edad="${grupoId}" data-sexo="${sexo}" oninput="this.value = this.value.replace(/[^0-9]/g, '')" style="${inputStyle}" placeholder=""></div>`;
}

// Función para crear una celda completa con ambos sexos (en línea horizontal)
function crearCeldaMatricula(tipoId, grupoId, valorM = '', valorF = '') {
    // Forzar layout horizontal y sin saltos de línea
    return `<div class="matricula-pair-horizontal">${crearInputMatricula(tipoId, grupoId, 'M', valorM)}${crearInputMatricula(tipoId, grupoId, 'F', valorF)}</div>`;
}
