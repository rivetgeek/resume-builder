import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { BuilderApp } from "@/components/BuilderApp";

function devNoAuth(): boolean {
  const v =
    process.env.RESUME_BUILDER_DEV_NO_AUTH ||
    process.env.NEXT_PUBLIC_RESUME_BUILDER_DEV_NO_AUTH ||
    "";
  return ["1", "true", "yes"].includes(v.trim().toLowerCase());
}

export default function HomePage() {
  if (!devNoAuth() && !cookies().get("resume_session")) {
    redirect("/login");
  }
  return <BuilderApp />;
}
