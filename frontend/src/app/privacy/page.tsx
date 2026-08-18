export const metadata = {
  title: "Política de Privacidad | TallyNorth",
  description: "Política de privacidad de TallyNorth.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <article className="space-y-8 text-foreground">
        <header className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">Política de Privacidad</h1>
          <p className="text-sm text-muted-foreground">Última actualización: 18 de agosto de 2026</p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Alcance</h2>
          <p className="leading-7 text-muted-foreground">
            Esta política describe cómo TallyNorth trata la información cuando una persona usa la aplicación
            web o conecta su cuenta con integraciones externas, incluido un GPT personalizado de ChatGPT.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Información que tratamos</h2>
          <p className="leading-7 text-muted-foreground">
            TallyNorth puede tratar datos de cuenta, como el correo electrónico y credenciales protegidas,
            junto con la información financiera que el usuario decide registrar, como cuentas, movimientos,
            categorías, tarjetas, cuotas, recurrencias, presupuestos, metas e inversiones.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. Uso de la información</h2>
          <p className="leading-7 text-muted-foreground">
            La información se utiliza para autenticar al usuario, operar las funciones de TallyNorth, mantener
            el aislamiento entre cuentas y ejecutar las acciones que el usuario solicita. No se utiliza para
            vender datos personales ni financieros a terceros.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. Integración con ChatGPT</h2>
          <p className="leading-7 text-muted-foreground">
            Si el usuario conecta TallyNorth con un GPT de ChatGPT, TallyNorth recibe solicitudes autenticadas
            para consultar o modificar únicamente los datos asociados a la cuenta autorizada. El acceso se
            limita a los permisos concedidos y puede revocarse desde TallyNorth.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Compartición y terceros</h2>
          <p className="leading-7 text-muted-foreground">
            TallyNorth puede depender de proveedores de infraestructura necesarios para prestar el servicio,
            como servicios de hosting y base de datos. Estos proveedores procesan información únicamente en
            la medida necesaria para operar la aplicación. Cuando el usuario utiliza ChatGPT, el tratamiento
            realizado por OpenAI también está sujeto a las políticas y términos de OpenAI.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">6. Seguridad</h2>
          <p className="leading-7 text-muted-foreground">
            TallyNorth utiliza controles de autenticación y separación por usuario para evitar que una cuenta
            acceda a los datos de otra. Los secretos de integración se almacenan de forma protegida y pueden
            expirar o revocarse.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">7. Conservación y eliminación</h2>
          <p className="leading-7 text-muted-foreground">
            La información se conserva mientras sea necesaria para prestar el servicio o hasta que sea
            eliminada conforme a las funcionalidades disponibles y obligaciones técnicas aplicables. Los
            tokens de integración pueden revocarse en cualquier momento.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">8. Cambios en esta política</h2>
          <p className="leading-7 text-muted-foreground">
            Esta política puede actualizarse cuando cambien las funciones de TallyNorth o sus integraciones.
            La fecha de última actualización se mostrará al comienzo de esta página.
          </p>
        </section>
      </article>
    </main>
  );
}
