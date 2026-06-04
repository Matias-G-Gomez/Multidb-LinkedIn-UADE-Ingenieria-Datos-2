-- ============================================================
-- LINKEDIN TP - PostgreSQL
-- Todas las entidades del DLR + datos de prueba
-- ============================================================

-- TABLAS

CREATE TABLE usuario (
    idUsuario     SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    apellido      VARCHAR(100) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    fechaNacimiento DATE,
    ubicacion     VARCHAR(100),
    fotoPerfil    VARCHAR(255),
    creadoEn      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE empresa (
    idEmpresa     SERIAL PRIMARY KEY,
    nombre        VARCHAR(150) NOT NULL,
    descripcion   TEXT,
    ubicacion     VARCHAR(100),
    rubro         VARCHAR(100)
);

CREATE TABLE empleo (
    idEmpleo          SERIAL PRIMARY KEY,
    idEmpresa         INT REFERENCES empresa(idEmpresa),
    titulo            VARCHAR(150) NOT NULL,
    descripcion       TEXT,
    ubicacion         VARCHAR(100),
    modalidad         VARCHAR(50),
    fechaPublicacion  DATE DEFAULT CURRENT_DATE
);

CREATE TABLE postulacion (
    idPostulacion     SERIAL PRIMARY KEY,
    idUsuario         INT REFERENCES usuario(idUsuario),
    idEmpleo          INT REFERENCES empleo(idEmpleo),
    fechaPostulacion  DATE DEFAULT CURRENT_DATE,
    estado            VARCHAR(50) DEFAULT 'pendiente'
);

CREATE TABLE experiencia_laboral (
    idExperiencia  SERIAL PRIMARY KEY,
    idUsuario      INT REFERENCES usuario(idUsuario),
    idEmpresa      INT REFERENCES empresa(idEmpresa),
    puesto         VARCHAR(150),
    fechaInicio    DATE,
    fechaFin       DATE,
    descripcion    TEXT
);

CREATE TABLE educacion (
    idEducacion   SERIAL PRIMARY KEY,
    idUsuario     INT REFERENCES usuario(idUsuario),
    institucion   VARCHAR(150),
    titulo        VARCHAR(150),
    fechaInicio   DATE,
    fechaFin      DATE
);

CREATE TABLE habilidad (
    idHabilidad  SERIAL PRIMARY KEY,
    nombre       VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE usuario_habilidad (
    idUsuario    INT REFERENCES usuario(idUsuario),
    idHabilidad  INT REFERENCES habilidad(idHabilidad),
    PRIMARY KEY (idUsuario, idHabilidad)
);

-- ============================================================
-- DATOS DE PRUEBA
-- ============================================================

-- Usuarios
INSERT INTO usuario (nombre, apellido, email, fechaNacimiento, ubicacion, creadoEn) VALUES
('Matías',   'García',    'matias@mail.com',   '1999-03-15', 'Buenos Aires', '2024-06-01'),
('Diego',    'López',     'diego@mail.com',    '1998-07-22', 'Córdoba',      '2024-08-15'),
('Valentina','Martínez',  'vale@mail.com',     '2000-01-10', 'Buenos Aires', '2024-09-01'),
('Lucas',    'Fernández', 'lucas@mail.com',    '1997-11-05', 'Rosario',      '2024-11-20'),
('Sofía',    'Torres',    'sofia@mail.com',    '2001-04-18', 'Buenos Aires', '2025-01-10'),
('Andrés',   'Rodríguez', 'andres@mail.com',   '1996-09-30', 'Mendoza',      '2025-02-05'),
('Camila',   'Sánchez',   'camila@mail.com',   '1999-12-25', 'Buenos Aires', '2025-03-15'),
('Facundo',  'Pérez',     'facu@mail.com',     '1995-05-14', 'Córdoba',      '2025-04-01');

-- Empresas
INSERT INTO empresa (nombre, descripcion, ubicacion, rubro) VALUES
('MercadoLibre', 'E-commerce líder en LATAM',           'Buenos Aires', 'Tecnología'),
('Globant',      'Empresa de software y IT',             'Buenos Aires', 'Tecnología'),
('Santander',    'Banco multinacional',                  'Buenos Aires', 'Finanzas'),
('Accenture',    'Consultoría y tecnología',             'Buenos Aires', 'Consultoría'),
('Google',       'Empresa de tecnología global',         'Buenos Aires', 'Tecnología'),
('Despegar',     'Plataforma de viajes online',          'Buenos Aires', 'Tecnología');

-- Empleos
INSERT INTO empleo (idEmpresa, titulo, descripcion, ubicacion, modalidad, fechaPublicacion) VALUES
(1, 'Backend Developer',        'Desarrollo en Java y Python',       'Buenos Aires', 'híbrido',  '2025-03-01'),
(1, 'Data Analyst',             'Análisis de datos con SQL y Python', 'Buenos Aires', 'remoto',   '2025-03-10'),
(2, 'Frontend Developer',       'React y TypeScript',                'Buenos Aires', 'híbrido',  '2025-02-15'),
(2, 'DevOps Engineer',          'CI/CD, Docker, Kubernetes',         'Buenos Aires', 'remoto',   '2025-04-01'),
(3, 'Analista de Sistemas',     'Relevamiento y documentación',      'Buenos Aires', 'presencial','2025-01-20'),
(4, 'Tech Lead',                'Liderazgo de equipos de desarrollo', 'Buenos Aires', 'híbrido',  '2025-03-25'),
(5, 'Software Engineer',        'Desarrollo full stack',             'Buenos Aires', 'remoto',   '2025-04-10'),
(6, 'Product Manager',          'Gestión de producto digital',       'Buenos Aires', 'híbrido',  '2025-02-28');

-- Postulaciones
INSERT INTO postulacion (idUsuario, idEmpleo, fechaPostulacion, estado) VALUES
(1, 1, '2025-03-05', 'pendiente'),
(1, 3, '2025-03-12', 'rechazado'),
(2, 2, '2025-03-15', 'pendiente'),
(3, 4, '2025-04-02', 'aceptado'),
(4, 5, '2025-02-01', 'pendiente'),
(5, 7, '2025-04-11', 'pendiente'),
(6, 6, '2025-03-26', 'pendiente'),
(7, 8, '2025-03-01', 'rechazado');

-- Experiencia laboral
INSERT INTO experiencia_laboral (idUsuario, idEmpresa, puesto, fechaInicio, fechaFin, descripcion) VALUES
(1, 2, 'Desarrollador Junior',  '2023-01-01', '2024-01-01', 'Desarrollo frontend con React'),
(2, 3, 'Analista de Datos',     '2022-06-01', '2024-06-01', 'Reportes y dashboards en Power BI'),
(3, 1, 'QA Tester',             '2023-03-01', NULL,         'Testing automatizado con Selenium'),
(4, 4, 'Consultor IT',          '2021-01-01', '2023-12-31', 'Relevamiento de procesos'),
(5, 5, 'Intern SWE',            '2024-07-01', NULL,         'Desarrollo interno en Go'),
(6, 6, 'Product Analyst',       '2022-01-01', '2024-01-01', 'Análisis de métricas de producto');

-- Educación
INSERT INTO educacion (idUsuario, institucion, titulo, fechaInicio, fechaFin) VALUES
(1, 'UADE', 'Lic. Gestión de Tecnología de la Información', '2021-03-01', NULL),
(1, 'UADE', 'Tecnicatura en Desarrollo de Software',        '2022-03-01', NULL),
(2, 'UBA',  'Ingeniería en Informática',                    '2020-03-01', NULL),
(3, 'UTN',  'Analista en Sistemas',                         '2021-03-01', '2024-12-01'),
(4, 'UNC',  'Licenciatura en Sistemas',                     '2018-03-01', '2023-12-01'),
(5, 'ITBA', 'Ingeniería Informática',                       '2022-03-01', NULL);

-- Habilidades
INSERT INTO habilidad (nombre) VALUES
('Python'), ('SQL'), ('Java'), ('React'), ('Docker'),
('Machine Learning'), ('Node.js'), ('MongoDB'), ('AWS'), ('Marketing Digital');

-- Usuario - Habilidad
INSERT INTO usuario_habilidad (idUsuario, idHabilidad) VALUES
(1, 1), (1, 2), (1, 4), (1, 5),
(2, 1), (2, 2), (2, 6),
(3, 4), (3, 7),
(4, 2), (4, 3),
(5, 1), (5, 5), (5, 9),
(6, 10), (6, 2),
(7, 1), (7, 4), (7, 7),
(8, 3), (8, 2), (8, 5);