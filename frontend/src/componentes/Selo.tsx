export default function Selo({ ativo }: { ativo: boolean }) {
  if (!ativo) return null;
  return (
    <div className="selo-demo" role="status">
      DEMONSTRAÇÃO · dados simulados
    </div>
  );
}
