def parse_coord(s)
  s.split(",").map do |s|
    if s.include?("/")
      num, den = s.split("/").map {|v| v.to_f }
      v = (num / den).to_s.gsub(/^0+/, "")
      [v, s.chomp].min_by {|t| t.size }
    else
      s.chomp
    end
  end
end

def parse_problem(file)
  lines = File.readlines(file)
  polygons, holes = [], []
  lines.shift.to_i.times do
    vertices = (0...lines.shift.to_i).map do
      parse_coord(lines.shift)
    end

    area = 0.0
    (vertices + [vertices[0]]).each_cons(2) do |p0, p1|
      area += (Complex(*p0) * Complex(*p1).conj).imag
    end
    (area < 0 ? polygons : holes) << vertices
  end
  segments = (0...lines.shift.to_i).map do
    s = lines.shift.split(" ")
    [parse_coord(s[0]), parse_coord(s[1])]
  end
  "[#{ dump(polygons) },#{ dump(holes) },#{ dump(segments) }]"
end

def dump(ary)
  if ary.is_a?(Array)
    "[#{ ary.map {|v| dump(v) }.join(",") }]"
  else
    ary
  end
end

problems = "var problems={#{
  {
    "sample" => "sample.txt",
    "small_square" => "../tasks/A-10.txt",
    "decagon" => "../tasks/D-10.txt",
    "donut" => "donut.txt",
    "crane" => "crane.txt",
  }.map do |id, file|
    "#{ id }:#{ parse_problem(file) }"
  end.join(",")
}};"

src = File.read("play.src.js")

src = src.gsub(%r(// problem definition.*\n.*), "")

src = src.gsub(%r(//.*), "")

src = src.gsub(%r(\(function\(root\) *(?<paren>\{(?:[^{}]|\g<paren>)*\})\)\(this\);), "")
src = src.gsub(%r(function fold\b.*(?<paren>\{(?:[^{}]|\g<paren>)*\})), "")
src = src.gsub(%r(function push\b.*(?<paren>\{(?:[^{}]|\g<paren>)*\})), "")
src = src.gsub(%r(function literal\b.*(?<paren>\{(?:[^{}]|\g<paren>)*\})), "")

nil while src.gsub!(%r(new (?:Complex|Point|Facet)(?<paren>\((?:[^()]|\g<paren>)*\)))) { "[#{ $~[:paren][1..-2] }]" }

src = src.gsub(%r(\.(?:re|src|front)\b), "[0]")
src = src.gsub("img[0]", "img.src")
src = src.gsub(%r(\.(?:im|dst|points)\b), "[1]")
src = src.gsub('"src"', "0")
src = src.gsub('== "dst"', "")
src = src.gsub('"dst"', "1")

src = src.gsub(%r(\.polygons\b), "[0]")
src = src.gsub(%r(\.holes\b), "[1]")
src = src.gsub(%r(\.segments\b), "[2]")

src = src.gsub(/\bfalse\b/, "!1")
src = src.gsub(/\btrue\b/, "!0")

keywords = %w(
addClass atan2 beginPath clearRect click clip closePath concat data drawImage else fillRect fill fillStyle fold function getContext globalCompositeOperation height if length lineTo lineWidth mousedown mousemove mouseup bind originalEvent pageX pageY changedTouches touchstart touchmove touchend moveTo new null position offset offsetX offsetY offsetLeft offsetTop left top getBoundingClientRect onload parent pop preventDefault push remove removeClass restore return reverse rotate save setTransform shift src stroke strokeStyle this translate true unshift var width
problem1 problem2 problem3
)
#keywords = src.gsub(/literal(?<paren>\((?:[^()]|\g<paren>)*\))/, "").scan(/\b[a-z]\w*\b/).sort.uniq - keywords
##p *keywords
#keywords.each do |keyword|
  #src = src.gsub(/\b#{ keyword }\b/, "_")
#end
#$stderr.puts "keywords: #{ keywords.size }"
##p *keywords

srand(0)
rename = {}
vs = [*"A".."Z"].shuffle #- keywords
#p vs
src.scan(/^(?:var|function) +([\w\d]+)/) do |ident,|
  rename[ident] = vs.shift
end
%w(cur_state state_stack flipped imgs).each do |ident|
  rename[ident] = vs.shift
end

#p *rename
#p *(keywords - rename.keys).zip(vs)

funcs = []
src = src.gsub(%r(^function \w+\((?<params>.*)\)*(?<paren>\{(?:[^{}]|\g<paren>)*\}))) do
  s = $&
  ks = ($~[:params] + " " + $~[:paren]).gsub(/literal(?<paren>\((?:[^()]|\g<paren>)*\))/, "").scan(/\b[a-z]\w*\b/).uniq - keywords - rename.keys
  local_rename = {}
  vs = [*"a".."z"].shuffle
  ks.each do |k|
    local_rename[k] = vs.shift
  end
  funcs << s.gsub(/(?<ident>\b(?:#{ ks.join("|") })\b)|literal(?<paren>\((?:[^()]|\g<paren>)*\))/) do
    if $~[:paren]
      $&
    else
      #p ks
      #p [$~[:ident], local_rename[$~[:ident]]]
      local_rename[$~[:ident]]# + "/* #{ $~[:ident] } */"
    end
  end
  ""
end
src = funcs.shuffle.join + src
s = rename.keys.join("|")
src = src.gsub(/(?<ident>\b(?:#{ s })\b)|literal(?<paren>\((?:[^()]|\g<paren>)*\))/) do
  if $~[:paren]
    $~[:paren][1..-2]
  else
    rename[$~[:ident]]
  end
end
#puts src

# 空白とる
s = []
quote = false
src.split.each do |v|
  if quote || (s.last && s.last =~ /\w$/ && v =~ /^(\w|\$)/)
    s << (" " + v)
  else
    s << v
  end
  quote = !quote if v.count('"').odd?
end
src = s.join.b
src = src.gsub(";}", "}")
src = src.gsub(/\b0(\.\d+)/) { $1 }
puts src

$stderr.puts src.size
#puts <<END
#function fold(l, z, f) {
#    for (var i = 0; i < l.length; i++) z = f(z, l[i]);
#    return z;
#}
#
#function push(l, x) {
#    l = l.concat();
#    l.push(x);
#    return l;
#}
##{ src }
#END
#exit

src = "/* Not so hard to deobfuscate this code, but you will gain nothing by it. */" + src
# BPE compression
keys = []
(512+31).downto(126) do |x|
  h = Hash.new(0)
  src.chars.each_cons(2) do |b|
    h[b] += 1
  end
  k, v = h.max_by {|k, v| v }
  k = k.join
  keys << k
  src = src.gsub(k) { (x & 511).chr("UTF-8") }
end
$stderr.puts src.size
h = {
  "001" => "I", "011" => "C", "010" => "F", "000" => "P",
  "101" => "i", "111" => "c", "110" => "f", "100" => "p",
}
src = (keys.reverse.join + src).chars.map do |c|
  c = c.ord
  (0..2).map do |i|
    h["%03b" % ((c >> (6 - i * 3)) & 7)]
  end.join
end.join
#File.write("play.js", DATA.read.gsub("SRC", src))
src = DATA.read.gsub("SRC", src)
src = src.gsub("PROBLEMS", problems)
File.write("play.js", src)

__END__
function fold(l, z, f) {
    for (var i = 0; i < l.length; i++) z = f(z, l[i]);
    return z;
}

function push(l, x) {
    l = l.concat();
    l.push(x);
    return l;
}

PROBLEMS

eval(fold(fold(Array.apply(null,{length:418}),[fold(

"SRC"

,[[],1],function(z,n){n=n.charCodeAt(0);n=z[1]*8+(n<99?0:4)+n%4;return(n>511?[push(z[0],n%512),1]:[z[0],n])})[0],0],function(z,v){return[z[0].slice(0,836).concat(fold(z[0].slice(836),[],function(l,v){(z[1]+126)%512==v?(l.push(z[0][z[1]*2])+l.push(z[0][z[1]*2+1])):l.push(v);return l})),z[1]+1]})[0].slice(836),"",function(z,v){return(z+String.fromCharCode(v))}))
