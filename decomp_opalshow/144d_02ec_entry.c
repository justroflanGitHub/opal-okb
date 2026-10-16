
/* WARNING: Stack frame is not setup normally: Input value of stackpointer is not used */
/* WARNING: This function may have set the stack pointer */

void __cdecl16near entry(void)

{
  undefined1 *puVar1;
  code *pcVar2;
  byte bVar3;
  int iVar4;
  undefined1 *puVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  uint uVar8;
  undefined1 *puVar9;
  undefined2 uVar10;
  undefined2 unaff_DS;
  
  puVar5 = (undefined1 *)0x800;
  pcVar2 = (code *)swi(0x21);
  bVar3 = (*pcVar2)();
  if (bVar3 < 2) {
    pcVar2 = (code *)swi(0x20);
    (*pcVar2)();
  }
  uVar8 = *(int *)0x2 + 0xe772;
  if (0xfff < uVar8) {
    uVar8 = 0x1000;
  }
  puVar6 = puVar5 + 0x161e;
  puVar9 = puVar5 + 0x161e;
  if ((undefined1 *)0xe9e1 < puVar5) {
    *(undefined2 *)(puVar5 + 0x161c) = 0x188e;
    unaff_DS = *(undefined2 *)(puVar5 + 0x161c);
    *(undefined2 *)(puVar5 + 0x161c) = 0x144d;
    *(undefined2 *)(puVar5 + 0x161a) = 0x47e9;
    FUN_144d_054a();
    *(undefined2 *)(puVar5 + 0x161c) = 0;
    *(undefined2 *)(puVar5 + 0x161a) = 0x144d;
    *(undefined2 *)(puVar5 + 0x1618) = 0x47f1;
    FUN_144d_05bf();
    pcVar2 = (code *)swi(0x21);
    (*pcVar2)();
    puVar9 = puVar6;
  }
  puVar7 = (undefined1 *)((uint)puVar9 & 0xfffe);
  iRam00018c1c = uVar8 * 0x10 + -1;
  puRam00018c1e = puVar7;
  puRam00018c22 = puVar7;
  *(int *)0x2 = uVar8 + 0x188e;
  pcVar2 = (code *)swi(0x21);
  (*pcVar2)();
  DAT_188e_03b3 = unaff_DS;
  *(undefined2 *)(puVar7 + -2) = 0x188e;
  uVar10 = *(undefined2 *)(puVar7 + -2);
  puVar9 = (undefined1 *)0xfec;
  for (iVar4 = 0x634; iVar4 != 0; iVar4 = iVar4 + -1) {
    puVar1 = puVar9;
    puVar9 = puVar9 + 1;
    *puVar1 = 0;
  }
  *(undefined2 *)(puVar7 + -2) = 0x188e;
  *(undefined2 *)(puVar7 + -2) = 0x144d;
  *(undefined2 *)(puVar7 + -4) = 0x4839;
  FUN_144d_05f6();
  *(undefined2 *)(puVar7 + -2) = 0x144d;
  *(undefined2 *)(puVar7 + -4) = 0x483e;
  FUN_1000_0898();
  *(undefined2 *)(puVar7 + -2) = 0x1089;
  *(undefined2 *)(puVar7 + -4) = 0x4843;
  FUN_144d_03ce();
  *(undefined2 *)(puVar7 + -2) = 0x188e;
  uVar10 = *(undefined2 *)(puVar7 + -2);
  *(undefined2 *)(puVar7 + -2) = *(undefined2 *)0x3d8;
  *(undefined2 *)(puVar7 + -4) = *(undefined2 *)0x3d6;
  *(undefined2 *)(puVar7 + -6) = *(undefined2 *)0x3d4;
  *(undefined2 *)(puVar7 + -8) = *(undefined2 *)0x3d2;
  *(undefined2 *)(puVar7 + -10) = *(undefined2 *)0x3d0;
  *(undefined2 *)(puVar7 + -0xc) = 0x144d;
  *(undefined2 *)(puVar7 + -0xe) = 0x4860;
  uVar10 = FUN_1089_000a();
  *(undefined2 *)(puVar7 + -0xc) = uVar10;
  *(undefined2 *)(puVar7 + -0xe) = 0x1089;
  *(undefined2 *)(puVar7 + -0x10) = 0x4866;
  FUN_144d_0499();
  return;
}

