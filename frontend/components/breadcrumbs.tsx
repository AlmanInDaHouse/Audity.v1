import Link from 'next/link';

type Crumb = {
  label: string;
  href?: string;
};

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`}>
            {item.href && !isLast ? <Link href={item.href}>{item.label}</Link> : item.label}
            {!isLast && <span style={{ margin: '0 6px' }}>/</span>}
          </span>
        );
      })}
    </nav>
  );
}
