// GENERADO por stock-profit-os/scripts/export_web_config.py — NO EDITAR A MANO.
// Regenerar con: npm run gen:config
export const ENGINE_CONFIG = {
  "familyLabels": {
    "dermocosmetica": "Dermocosmética",
    "higiene": "Higiene",
    "medicamento_receta": "Medicamento con receta",
    "nutricion": "Nutrición",
    "ortopedia": "Ortopedia",
    "otc": "OTC",
    "otros": "Otros",
    "solares": "Solares"
  },
  "mappings": {
    "farmatic": {
      "familias": {
        "Dermocosmética": "dermocosmetica",
        "Dermofarmacia": "dermocosmetica",
        "Dietética y Nutrición": "nutricion",
        "EFP": "otc",
        "EFP / Publicitarios": "otc",
        "Especialidad": "medicamento_receta",
        "Especialidad con receta": "medicamento_receta",
        "Higiene": "higiene",
        "Nutrición": "nutricion",
        "Ortopedia": "ortopedia",
        "Publicitarios": "otc",
        "Solares": "solares"
      },
      "ficheros": {
        "compras": {
          "codigo_nacional": [
            "Código",
            "Codigo",
            "Cód. Nacional",
            "CN"
          ],
          "coste_total": [
            "Importe Coste",
            "Total Coste",
            "Importe"
          ],
          "fecha": [
            "Fecha Albarán",
            "Fecha Albaran",
            "Fecha"
          ],
          "laboratorio": [
            "Laboratorio",
            "Lab."
          ],
          "unidades": [
            "Unidades Recibidas",
            "Unidades",
            "Uds."
          ]
        },
        "stock": {
          "codigo_nacional": [
            "Código",
            "Codigo",
            "Cód. Nacional",
            "CN"
          ],
          "coste_unitario": [
            "P.Coste",
            "PVC",
            "Precio Coste"
          ],
          "descripcion": [
            "Descripción",
            "Descripcion",
            "Artículo"
          ],
          "familia": [
            "Familia"
          ],
          "fecha_caducidad": [
            "Caducidad",
            "F. Caducidad",
            "Fecha Caducidad"
          ],
          "laboratorio": [
            "Laboratorio",
            "Lab."
          ],
          "pvp": [
            "PVP",
            "P.V.P."
          ],
          "stock_unidades": [
            "Stock Actual",
            "Stock",
            "Existencias"
          ]
        },
        "ventas": {
          "codigo_nacional": [
            "Código",
            "Codigo",
            "Cód. Nacional",
            "CN"
          ],
          "coste_unitario": [
            "P.Coste",
            "PVC",
            "Precio Coste"
          ],
          "descripcion": [
            "Descripción",
            "Descripcion",
            "Artículo"
          ],
          "familia": [
            "Familia"
          ],
          "fecha": [
            "Fecha",
            "Fecha Venta"
          ],
          "importe_venta_sin_iva": [
            "Importe s/IVA",
            "Importe sin IVA",
            "Base Imponible"
          ],
          "laboratorio": [
            "Laboratorio",
            "Lab."
          ],
          "unidades": [
            "Unidades",
            "Uds.",
            "Cantidad"
          ]
        }
      },
      "lectura": {
        "decimal": ",",
        "encoding": "cp1252",
        "formato_fecha": "%d/%m/%Y",
        "miles": ".",
        "separador": ";"
      }
    },
    "nixfarma": {
      "familias": {
        "Dermocosmética": "dermocosmetica",
        "Fotoprotección": "solares",
        "Higiene": "higiene",
        "Medicamentos con receta": "medicamento_receta",
        "Medicamentos sin receta": "otc",
        "Nutrición": "nutricion",
        "Ortopedia": "ortopedia"
      },
      "ficheros": {
        "compras": {
          "codigo_nacional": [
            "COD_NACIONAL",
            "CODIGO"
          ],
          "coste_total": [
            "IMPORTE_COSTE",
            "TOTAL_COSTE"
          ],
          "fecha": [
            "FECHA_ENTRADA",
            "FECHA"
          ],
          "laboratorio": [
            "LABORATORIO",
            "NOMBRE_LAB"
          ],
          "unidades": [
            "CANTIDAD",
            "UNIDADES"
          ]
        },
        "stock": {
          "codigo_nacional": [
            "COD_NACIONAL",
            "CODIGO"
          ],
          "coste_unitario": [
            "PRECIO_COSTE",
            "PMC"
          ],
          "descripcion": [
            "DESCRIPCION",
            "DENOMINACION"
          ],
          "familia": [
            "FAMILIA",
            "SUBFAMILIA"
          ],
          "fecha_caducidad": [
            "FECHA_CADUCIDAD",
            "CADUCIDAD"
          ],
          "laboratorio": [
            "LABORATORIO",
            "NOMBRE_LAB"
          ],
          "pvp": [
            "PVP"
          ],
          "stock_unidades": [
            "STOCK",
            "EXISTENCIAS"
          ]
        },
        "ventas": {
          "codigo_nacional": [
            "COD_NACIONAL",
            "CODIGO"
          ],
          "coste_unitario": [
            "PRECIO_COSTE",
            "PMC"
          ],
          "descripcion": [
            "DESCRIPCION",
            "DENOMINACION"
          ],
          "familia": [
            "FAMILIA",
            "SUBFAMILIA"
          ],
          "fecha": [
            "FECHA_VENTA",
            "FECHA"
          ],
          "importe_venta_sin_iva": [
            "IMP_NETO",
            "IMPORTE_SIN_IVA"
          ],
          "laboratorio": [
            "LABORATORIO",
            "NOMBRE_LAB"
          ],
          "unidades": [
            "CANTIDAD",
            "UNIDADES"
          ]
        }
      },
      "lectura": {
        "decimal": ",",
        "encoding": "utf-8",
        "formato_fecha": "%d/%m/%Y",
        "miles": "",
        "separador": ";"
      }
    }
  },
  "privacyContent": {
    "dni": "\\d{8}[ -]?[A-HJ-NP-TV-Z]",
    "email": "[^@\\s]+@[^@\\s]+\\.[A-Za-z]{2,}",
    "nie": "[XYZ][ -]?\\d{7}[ -]?[A-HJ-NP-TV-Z]",
    "phone": "(\\+34|0034)?[ -]?[6789]\\d{2}[ -]?\\d{3}[ -]?\\d{3}"
  },
  "privacyHeaderRules": [
    {
      "category": "identidad",
      "pattern": "\\b(dni|nie|nif|d n i|n i e|n i f|pasaporte|documento (de )?identidad|doc identidad)\\b",
      "reason": "parece un documento de identidad (DNI/NIE/NIF/pasaporte)"
    },
    {
      "category": "tarjeta_sanitaria",
      "pattern": "\\b(cip|cipa|cip sns|cip autonomico|sip|tsi|tarjeta sanitaria|tarjeta individual sanitaria|seguridad social|nss|naf|n afiliacion|numero afiliacion)\\b",
      "reason": "parece un identificador sanitario (CIP, tarjeta sanitaria o nº de la Seguridad Social)"
    },
    {
      "category": "receta",
      "pattern": "\\b(recetas?|n receta|num receta|numero receta|id receta|codigo receta|prescripcion)\\b",
      "reason": "parece un número o identificador de receta, ligado a un paciente"
    },
    {
      "category": "paciente",
      "pattern": "\\b(pacientes?|apellidos?|clientes?|nombre (del |de la )?(paciente|cliente|titular|usuario|persona|comprador))\\b",
      "reason": "identifica a una persona (paciente o cliente)"
    },
    {
      "category": "datos_personales",
      "pattern": "\\b(fecha (de )?nacimiento|f nacimiento|f nac|nacimiento|edad|sexo|genero)\\b",
      "reason": "contiene datos personales (nacimiento, edad o sexo)"
    },
    {
      "category": "datos_sanitarios",
      "pattern": "\\b(diagnostico|patologia|enfermedad|alergias?|historia clinica|hce|tratamiento cronico)\\b",
      "reason": "contiene datos de salud de una persona"
    },
    {
      "category": "telefono",
      "pattern": "\\b(tel|tlf|tfno|telefono|telefonos|movil|celular|phone|fax)\\b",
      "reason": "parece un número de teléfono"
    },
    {
      "category": "email",
      "pattern": "\\b(e mail|email|mail|correo|correo electronico)\\b",
      "reason": "parece una dirección de correo electrónico"
    },
    {
      "category": "direccion",
      "pattern": "\\b(direccion|domicilio|calle|codigo postal|poblacion|localidad)\\b",
      "reason": "parece una dirección postal"
    }
  ],
  "schemas": {
    "compras": {
      "columns": [
        "fecha",
        "codigo_nacional",
        "laboratorio",
        "unidades",
        "coste_total"
      ],
      "required": [
        "fecha",
        "codigo_nacional",
        "unidades",
        "coste_total"
      ]
    },
    "stock": {
      "columns": [
        "codigo_nacional",
        "descripcion",
        "laboratorio",
        "familia",
        "stock_unidades",
        "coste_unitario",
        "pvp",
        "fecha_caducidad"
      ],
      "required": [
        "codigo_nacional",
        "stock_unidades",
        "coste_unitario"
      ]
    },
    "ventas": {
      "columns": [
        "fecha",
        "codigo_nacional",
        "descripcion",
        "laboratorio",
        "familia",
        "unidades",
        "importe_venta_sin_iva",
        "coste_unitario"
      ],
      "required": [
        "fecha",
        "codigo_nacional",
        "unidades",
        "importe_venta_sin_iva"
      ]
    }
  },
  "synonyms": {
    "codigo_nacional": [
      "codigo nacional",
      "cod nacional",
      "cn",
      "codigo",
      "cod articulo",
      "codigo articulo",
      "cod producto",
      "referencia",
      "ref"
    ],
    "coste_total": [
      "importe coste",
      "coste total",
      "total coste",
      "importe compra",
      "total compra",
      "importe albaran",
      "importe"
    ],
    "coste_unitario": [
      "coste unitario",
      "precio coste",
      "p coste",
      "pvc",
      "pmc",
      "coste medio",
      "precio medio coste",
      "coste"
    ],
    "descripcion": [
      "descripcion",
      "denominacion",
      "articulo",
      "producto",
      "nombre articulo",
      "nombre producto",
      "desc"
    ],
    "familia": [
      "familia",
      "subfamilia",
      "categoria",
      "seccion",
      "grupo"
    ],
    "fecha": [
      "fecha",
      "fecha venta",
      "fecha operacion",
      "fecha albaran",
      "fecha entrada",
      "fecha recepcion",
      "dia",
      "f venta",
      "f albaran"
    ],
    "fecha_caducidad": [
      "caducidad",
      "fecha caducidad",
      "f caducidad",
      "cad",
      "vencimiento"
    ],
    "importe_venta_sin_iva": [
      "importe sin iva",
      "importe s iva",
      "base imponible",
      "importe neto",
      "venta neta",
      "imp neto",
      "total sin iva",
      "importe venta"
    ],
    "laboratorio": [
      "laboratorio",
      "lab",
      "proveedor",
      "fabricante",
      "marca"
    ],
    "pvp": [
      "pvp",
      "precio venta",
      "p v p",
      "pvp iva"
    ],
    "stock_unidades": [
      "stock",
      "stock actual",
      "existencias",
      "unidades stock",
      "stock disponible"
    ],
    "unidades": [
      "unidades",
      "uds",
      "cantidad",
      "cant",
      "unidades vendidas",
      "unidades recibidas",
      "unid"
    ]
  }
} as const;
