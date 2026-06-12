import AssistantDetailsClient from './ClientPage';

export function generateStaticParams() {
  return [
    { id: 'ast_101' },
    { id: 'ast_102' },
    { id: 'ast_103' },
    { id: 'ast_104' },
  ];
}

export default function AssistantDetailsPage() {
  return <AssistantDetailsClient />;
}
