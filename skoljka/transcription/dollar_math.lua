-- Do nothing unless we are targeting TeX.
if not FORMAT:match('tex$') then return {} end

function Math(m)
  if m.mathtype == 'InlineMath' then
    return pandoc.RawInline('tex', '$' .. m.text .. '$')
  elseif m.mathtype == 'DisplayMath' then
    return pandoc.RawInline('tex', '\\[' .. m.text .. '\\]')
  end
end
