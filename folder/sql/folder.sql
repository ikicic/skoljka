INSERT INTO `folder_folder` (`id`, `name`, `short_name`, `parent_id`) VALUES
    (1, 'root', 'root', NULL),
      (2, 'Natjecanja', 'Natjecanja', 1),
         (3, 'Olimpijade', 'Olimpijade', 2),
         (4, 'Hrvatska', 'Hrvatska', 2),
      (5, 'Kategorije', 'Kategorije', 1),
         (6, 'Algebra', 'Algebra', 5),
         (7, 'Kombinatorika', 'Kombinatorika', 5),
         (8, 'Geometrija', 'Geometrija', 5),
         (9, 'Teorija brojeva', 'Teorija brojeva', 5);
