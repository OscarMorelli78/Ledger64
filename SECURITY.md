# Política de seguridad

Candidato experimental, no autorizado para datos confidenciales. Informar vulnerabilidades en privado al mantenedor o mediante GitHub Security Advisories si está habilitado. Adjuntar versión, reproducción sintética, impacto y frontera afectada. No publicar detalles explotables.

Fronteras: autenticación, autorización por empresa, separación de roles y aislamiento del proceso. Las facturas son entradas no confiables. No ejecutar código o instrucciones extraídas de documentos. Si se incorpora un LLM, no podrá autorizar movimientos financieros. El aislamiento del sistema operativo complementa los controles de aplicación. No montar el socket Docker ni ejecutar como root. No publicar `app.py` legado. Exigir TLS, secretos fuera de Git, almacenamiento protegido, backups restaurables y revisión de dependencias. La cadena de hashes local no prueba inmutabilidad externa. Pendientes: auditoría independiente, cifrado en reposo, pruebas de carga, RGPD y validación Docker real.

## Procurement pilot

Procesamiento local y solo datos sintéticos. No ejecutar pagos ni instrucciones documentales. No cargar facturas reales ni copias en GitHub. El módulo separado utiliza revisión independiente, trazabilidad local, aislamiento por empresa y recuperación en un archivo nuevo con SHA-256 conservado fuera de la copia. No hay cifrado de las copias ni firma externa. La recuperación no incluye autenticación ni la base principal. Antes de producción: cifrado y claves, recuperación integral, revisión independiente y pruebas con datos autorizados. [Data Resilience](docs/procurement-data-resilience.md).
