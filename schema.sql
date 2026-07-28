-- Esquema para la Base de Datos de Inventario en Supabase (PostgreSQL)

-- 1. Crear extensión para UUID (si no existe)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Tabla Principal: inventario
CREATE TABLE IF NOT EXISTS public.inventario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    categoria VARCHAR(100) NOT NULL,
    concepto VARCHAR(150) NOT NULL,
    stock_ideal NUMERIC(10,2) DEFAULT 1.0,
    stock_actual NUMERIC(10,2) DEFAULT 0.0,
    unidad_medida VARCHAR(30) DEFAULT 'PZA',
    estatus VARCHAR(50) DEFAULT 'HAY EN CASA',
    notas TEXT DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_inventario_categoria ON public.inventario(categoria);
CREATE INDEX IF NOT EXISTS idx_inventario_estatus ON public.inventario(estatus);
CREATE INDEX IF NOT EXISTS idx_inventario_concepto ON public.inventario(concepto);

-- 4. Habilitar RLS (Row Level Security) y permitir acceso con Anon Key
ALTER TABLE public.inventario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir lectura publica de inventario" 
    ON public.inventario FOR SELECT 
    USING (true);

CREATE POLICY "Permitir insercion publica de inventario" 
    ON public.inventario FOR INSERT 
    WITH CHECK (true);

CREATE POLICY "Permitir actualizacion publica de inventario" 
    ON public.inventario FOR UPDATE 
    USING (true);

CREATE POLICY "Permitir eliminacion publica de inventario" 
    ON public.inventario FOR DELETE 
    USING (true);
