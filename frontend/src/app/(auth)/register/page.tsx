import { RegisterForm } from "./register-form";

type RegisterPageProps = {
  searchParams: Promise<{
    error?: string;
    next?: string;
  }>;
};

export default async function RegisterPage({ searchParams }: RegisterPageProps) {
  const params = await searchParams;

  return <RegisterForm hasError={Boolean(params.error)} next={params.next ?? "/"} />;
}
