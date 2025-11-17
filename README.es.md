<div align="center">

![MemU Banner](assets/banner.png)

### MemU: El Sistema de Memoria Agéntica de Nueva Generación

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Únete%20al%20chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Síguenos-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)
</div>

**MemU** es un sistema de memoria agente de próxima generación que rediseña la arquitectura de memoria de los agentes desde una perspectiva centrada en la memoria, abstrayéndola como una capa de datos que evoluciona dinámicamente y organiza y recupera información relevante de forma inteligente según el contexto.
A través de mecanismos adaptativos de recuperación y retroceso, extrae dinámicamente la información más pertinente.
El sistema utiliza una **Memoria Multimodal Unificada**, con soporte nativo para diferentes tipos de datos, incluidos texto, imágenes y audio, formando una representación de memoria cohesiva.

Visita nuestra página web: [memu.pro](https://memu.pro/)

---

## ⭐ Danos una estrella en GitHub

Dale una estrella a MemU para recibir notificaciones sobre nuevas versiones y únete a nuestra creciente comunidad de desarrolladores de IA que construyen agentes inteligentes con capacidades de memoria persistente.

![star-us](./assets/star.gif)

**💬 Únete a nuestra comunidad en Discord:** [https://discord.gg/memu](https://discord.gg/memu)

---

## 🚀 Comienza a usar MemU

Existen tres formas de comenzar con MemU:

### ☁️ Versión en la nube ([Plataforma en línea](https://app.memu.so))

La forma más rápida de integrar tu aplicación con memU. Perfecta para equipos e individuos que desean acceso inmediato sin la complejidad de configuración.
Nosotros alojamos los modelos, las API y el almacenamiento en la nube, asegurando que tu aplicación obtenga la mejor calidad de memoria IA.

- **Acceso instantáneo** – Comienza a integrar memorias de IA en minutos
- **Infraestructura gestionada** – Nos encargamos del escalado, actualizaciones y mantenimiento para una calidad óptima de memoria
- **Soporte premium** – Suscríbete y obtén asistencia prioritaria de nuestro equipo de ingeniería

### Paso a paso

**Paso 1:** Crear cuenta

Crea una cuenta en https://app.memu.so

Luego, visita https://app.memu.so/api-key/ para generar tus claves API.

**Paso 2:** Agrega tres líneas a tu código
```python
pip install memu-py

# Ejemplo de uso
from memu import MemuClient
```

**Paso 3:** Inicio rápido
```python
# Inicialización
memu_client = MemuClient(
    base_url="https://api.memu.so",
    api_key=os.getenv("MEMU_API_KEY")
)
memu_client.memorize_conversation(
    conversation=conversation_text, # Se recomienda una conversación larga (~8000 tokens), consulta https://memu.pro/blog/memu-best-practice para más detalles
    user_id="user001",
    user_name="User",
    agent_id="assistant001",
    agent_name="Assistant"
)
```
Consulta la [referencia de la API](docs/API_REFERENCE.md) o [nuestro blog](https://memu.pro/blog) para más detalles.

📖 **Consulta [`example/client/memory.py`](example/client/memory.py) para obtener detalles completos de integración**

✨ **¡Eso es todo!** MemU recuerda todo y ayuda a tu IA a aprender de conversaciones pasadas.

---

### 🏢 Edición Empresarial

Para organizaciones que requieren máxima seguridad, personalización, control y la mejor calidad:

- **Licencia Comercial** – Funcionalidades propietarias completas, derechos de uso comercial, opciones de marca blanca
- **Desarrollo Personalizado** – Integración SSO/RBAC, equipo dedicado de algoritmos para optimización de marcos específicos por escenario
- **Inteligencia y Analítica** – Análisis de comportamiento del usuario, monitoreo en tiempo real, optimización automática de agentes
- **Soporte Premium** – Soporte dedicado 24/7, SLA personalizados, servicios profesionales de implementación

📧 **Consultas empresariales:** [contact@nevamind.ai](mailto:contact@nevamind.ai)

---

### 🏠 Autoalojamiento (Edición Comunitaria)

Para usuarios y desarrolladores que prefieren control local, privacidad de datos o personalización:

* **Privacidad de Datos** – Mantén los datos sensibles dentro de tu infraestructura
* **Personalización** – Modifica y amplía la plataforma según tus necesidades
* **Control de Costos** – Evita tarifas recurrentes en la nube para implementaciones a gran escala

Consulta el [README de autoalojamiento](README.self_host.md)

---

## ✨ Funcionalidades Principales

### 🎥 Video de Demostración

<div align="left">
  <a href="https://www.youtube.com/watch?v=qZIuCoLglHs">
    <img src="https://img.youtube.com/vi/ueOe4ZPlZLU/maxresdefault.jpg" alt="MemU Demo Video" width="600">
  </a>
  <br>
  <em>Haz clic para ver el video demostrativo de MemU</em>
</div>

---

## 🎓 **Casos de Uso**

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="assets/usecase/ai_companion-0000.jpg" width="150" height="200"><br>**Compañero de IA** | <img src="assets/usecase/ai_role_play-0000.jpg" width="150" height="200"><br>**Juego de Roles con IA** | <img src="assets/usecase/ai_ip-0000.png" width="150" height="200"><br>**Personajes IP de IA** | <img src="assets/usecase/ai_edu-0000.jpg" width="150" height="200"><br>**Educación con IA** |
| <img src="assets/usecase/ai_therapy-0000.jpg" width="150" height="200"><br>**Terapia con IA** | <img src="assets/usecase/ai_robot-0000.jpg" width="150" height="200"><br>**Robot con IA** | <img src="assets/usecase/ai_creation-0000.jpg" width="150" height="200"><br>**Creación con IA** | Más...|

---

## 🤝 Contribuir

Construimos confianza a través de la colaboración de código abierto.
Tus contribuciones creativas impulsan la innovación de memU hacia adelante.
Explora nuestros issues e iniciativas en GitHub para comenzar y dejar tu huella en el futuro de memU.

📋 **[Lee nuestra guía detallada de contribución →](CONTRIBUTING.md)**

---

### 📄 **Licencia**

Al contribuir a MemU, aceptas que tus contribuciones se licencien bajo la **Licencia Apache 2.0**.

---

## 🌍 Comunidad

Para más información, contacta con [info@nevamind.ai](mailto:info@nevamind.ai)

- **GitHub Issues:** Reporta errores, solicita funciones y sigue el desarrollo. [Enviar un issue](https://github.com/NevaMind-AI/memU/issues)
- **Discord:** Obtén soporte en tiempo real, chatea con la comunidad y mantente actualizado. [Únete aquí](https://discord.com/invite/hQZntfGsbJ)
- **X (Twitter):** Síguenos para recibir actualizaciones, información sobre IA y anuncios clave. [Síguenos](https://x.com/memU_ai)

---

## 🤝 Ecosistema

Nos enorgullece trabajar con organizaciones increíbles:

<div align="center">

### Herramientas de Desarrollo

<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://github.com/openagents-org/openagents"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/camel-ai/camel"><img src="https://avatars.githubusercontent.com/u/134388954?s=200&v=4" alt="Camel" height="40" style="margin: 10px;"></a>
<a href="https://github.com/eigent-ai/eigent"><img src="https://www.eigent.ai/nav/logo_icon.svg" alt="Eigent" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="bytebase" height="40" style="margin: 10px;"></a>

</div>

---

*¿Interesado en asociarte con MemU? Contáctanos en [contact@nevamind.ai](mailto:contact@nevamind.ai)*

---

## 📱 Únete a Nuestra Comunidad en WeChat

Conéctate con nosotros en WeChat para recibir las últimas actualizaciones, discusiones comunitarias y contenido exclusivo:

<div align="center">
<img src="assets/qrcode.png" alt="MemU WeChat and discord QR Code" width="480" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px;">

*Escanea cualquiera de los códigos QR anteriores para unirte a nuestra comunidad en WeChat*

</div>

---

*¡Mantente conectado con la comunidad de MemU! Únete a nuestros grupos de WeChat para discusiones en tiempo real, soporte técnico y oportunidades de networking.*
