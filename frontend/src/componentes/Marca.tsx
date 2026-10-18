import branca from "../assets/match-branca.png";
import vermelha from "../assets/match-vermelha.png";

/** Logo do Match (wordmark). Vermelha sobre fundo claro; branca sobre o vermelho. */
export default function Marca({ cor = "vermelha", altura = 28, className = "" }: { cor?: "vermelha" | "branca"; altura?: number; className?: string }) {
  return (
    <img
      className={`marca ${className}`.trim()}
      src={cor === "branca" ? branca : vermelha}
      alt="Match"
      height={altura}
      style={{ height: altura, width: "auto" }}
      draggable={false}
    />
  );
}
