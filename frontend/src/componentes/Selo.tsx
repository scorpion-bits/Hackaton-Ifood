export default function Selo({ ativo, contaTeste }: { ativo: boolean; contaTeste?: boolean }) {
  if (ativo) {
    return (
      <div className="selo-demo" role="status">
        <i aria-hidden="true" />
        DEMONSTRAÇÃO · dados simulados
      </div>
    );
  }
  if (contaTeste) {
    return (
      <div className="selo-real" role="status">
        <i aria-hidden="true" />
        iFood real · conta de teste
      </div>
    );
  }
  return null;
}
